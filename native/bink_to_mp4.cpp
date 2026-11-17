// bink_to_mp4.cpp (custom, Nov 16): one of MCC's Bink 2 movies as an MP4 a web page can play (the Service Record's
// landing page plays MCC's Noble main-menu background, MCC\Content\Movies\NOBLE.bk2). The frames are decoded by MCC's
// own decoder (MCC\Binaries\Win64\bink2w64.dll, loaded from the game's folder, read only), halved, and encoded as
// H.264 by Windows' own Media Foundation; no sound (the page plays it muted). Nothing of the game is changed.
//
// usage: bink_to_mp4.exe <bink2w64.dll> <movie.bk2> <out.mp4> [width]       (width: of the MP4, default 1280)
//        bink_to_mp4.exe <bink2w64.dll> <movie.bk2> --frame <n> <out.png>   (one frame, to look at)
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <wincodec.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <string>

// Bink's movie handle starts with its size and length (bink.h: Width, Height, Frames, FrameNum, ...)
struct bink_head { unsigned Width, Height, Frames, FrameNum, LastFrameNum, FrameRate, FrameRateDiv; };
typedef bink_head* (__stdcall* BinkOpen_t)(const char*, unsigned);
typedef int (__stdcall* BinkDoFrame_t)(bink_head*);
typedef void (__stdcall* BinkNextFrame_t)(bink_head*);
typedef int (__stdcall* BinkCopyToBuffer_t)(bink_head*, void*, int, unsigned, unsigned, unsigned, unsigned);
typedef void (__stdcall* BinkClose_t)(bink_head*);
typedef void (__stdcall* BinkGoto_t)(bink_head*, unsigned, int);
static const unsigned SURFACE32 = 3;            // BINKSURFACE32: 4 bytes a pixel, blue first
static const unsigned COPYALL = 0x80000000u;    // BINKCOPYALL: the whole frame, not just what changed

static bool save_png(const std::vector<unsigned char>& bgra, unsigned w, unsigned h, const wchar_t* path) {
    IWICImagingFactory* wic = nullptr;
    if (FAILED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&wic)))) return false;
    IWICStream* s = nullptr; IWICBitmapEncoder* e = nullptr; IWICBitmapFrameEncode* f = nullptr;
    std::vector<unsigned char> px(bgra);                            // (opaque: the copy's fourth byte is not alpha)
    for (size_t k = 3; k < px.size(); k += 4) px[k] = 255;
    WICPixelFormatGUID fmt = GUID_WICPixelFormat32bppBGRA;
    bool ok = SUCCEEDED(wic->CreateStream(&s)) && SUCCEEDED(s->InitializeFromFilename(path, GENERIC_WRITE)) &&
              SUCCEEDED(wic->CreateEncoder(GUID_ContainerFormatPng, nullptr, &e)) && SUCCEEDED(e->Initialize(s, WICBitmapEncoderNoCache)) &&
              SUCCEEDED(e->CreateNewFrame(&f, nullptr)) && SUCCEEDED(f->Initialize(nullptr)) && SUCCEEDED(f->SetSize(w, h)) &&
              SUCCEEDED(f->SetPixelFormat(&fmt)) && IsEqualGUID(fmt, GUID_WICPixelFormat32bppBGRA) &&
              SUCCEEDED(f->WritePixels(h, w * 4, (UINT)px.size(), (BYTE*)px.data())) &&
              SUCCEEDED(f->Commit()) && SUCCEEDED(e->Commit());
    if (f) f->Release(); if (e) e->Release(); if (s) s->Release(); wic->Release();
    return ok;
}

// a w x h BGRA frame shrunk to ow x oh (each output pixel the mean of the source pixels under it), top row first
static void shrink(const unsigned char* src, unsigned w, unsigned h, unsigned char* dst, unsigned ow, unsigned oh) {
    for (unsigned y = 0; y < oh; y++) {
        unsigned y0 = y * h / oh, y1 = (y + 1) * h / oh;
        for (unsigned x = 0; x < ow; x++) {
            unsigned x0 = x * w / ow, x1 = (x + 1) * w / ow, n = 0, sum[3] = {};
            for (unsigned yy = y0; yy < y1; yy++)
                for (unsigned xx = x0; xx < x1; xx++, n++)
                    for (int c = 0; c < 3; c++) sum[c] += src[((size_t)yy * w + xx) * 4 + c];
            unsigned char* o = dst + ((size_t)y * ow + x) * 4;
            for (int c = 0; c < 3; c++) o[c] = (unsigned char)(sum[c] / (n ? n : 1));
            o[3] = 255;
        }
    }
}

int wmain(int argc, wchar_t** argv) {
    if (argc < 4) { fwprintf(stderr, L"usage: bink_to_mp4.exe <bink2w64.dll> <movie.bk2> <out.mp4> [width]\n"); return 2; }
    std::wstring dir = argv[1];
    size_t cut = dir.find_last_of(L"\\/");
    if (cut != std::wstring::npos) SetDllDirectoryW(dir.substr(0, cut).c_str());
    HMODULE dll = LoadLibraryW(argv[1]);
    if (!dll) { fwprintf(stderr, L"bink_to_mp4: cannot load %s\n", argv[1]); return 1; }
    auto open = (BinkOpen_t)GetProcAddress(dll, "BinkOpen");
    auto doframe = (BinkDoFrame_t)GetProcAddress(dll, "BinkDoFrame");
    auto next = (BinkNextFrame_t)GetProcAddress(dll, "BinkNextFrame");
    auto copy = (BinkCopyToBuffer_t)GetProcAddress(dll, "BinkCopyToBuffer");
    auto close = (BinkClose_t)GetProcAddress(dll, "BinkClose");
    auto go = (BinkGoto_t)GetProcAddress(dll, "BinkGoto");
    if (!open || !doframe || !next || !copy || !close || !go) { fwprintf(stderr, L"bink_to_mp4: not the Bink 2 decoder\n"); return 1; }
    char movie[MAX_PATH * 3];
    WideCharToMultiByte(CP_UTF8, 0, argv[2], -1, movie, sizeof movie, nullptr, nullptr);
    bink_head* b = open(movie, 0);
    if (!b) { fwprintf(stderr, L"bink_to_mp4: cannot open %s\n", argv[2]); return 1; }
    unsigned W = b->Width, H = b->Height, N = b->Frames;
    double fps = b->FrameRateDiv ? (double)b->FrameRate / b->FrameRateDiv : 30.0;
    printf("bink_to_mp4: %u x %u, %u frames, %.3f fps\n", W, H, N, fps);
    if (W < 16 || H < 16 || W > 8192 || H > 8192 || !N) { fwprintf(stderr, L"bink_to_mp4: the movie's size was not read\n"); close(b); return 1; }
    std::vector<unsigned char> frame((size_t)W * H * 4);
    if (FAILED(CoInitializeEx(nullptr, COINIT_MULTITHREADED))) return 1;

    if (argc >= 6 && !wcscmp(argv[3], L"--frame")) {             // one frame, to look at
        unsigned n = (unsigned)_wtoi(argv[4]);
        if (n < 1) n = 1;
        unsigned surface = argc >= 7 ? (unsigned)_wtoi(argv[6]) : SURFACE32;   // (a surface type to try)
        typedef const char* (__stdcall* BinkGetError_t)(void);
        auto err = (BinkGetError_t)GetProcAddress(dll, "BinkGetError");
        int d = 0, c = 0;
        for (unsigned k = 1; k <= n; k++) {                      // (frame by frame from the first: no seeking)
            d = doframe(b);
            if (k < n) next(b);
        }
        c = copy(b, frame.data(), (int)W * 4, H, 0, 0, surface | COPYALL);
        printf("doframe %d, copy %d, frame %u, error \"%s\"\n", d, c, b->FrameNum, err ? err() : "?");
        printf("bytes:");
        for (int k = 0; k < 16; k++) printf(" %02x", frame[(size_t)(H / 2) * W * 4 + 4000 + k]);
        printf("\n");
        bool ok = save_png(frame, W, H, argv[5]);
        close(b);
        printf(ok ? "frame %u written\n" : "frame %u not written\n", n);
        return ok ? 0 : 1;
    }

    unsigned OW = argc > 4 ? (unsigned)_wtoi(argv[4]) : 1280;
    if (OW < 64 || OW > W) OW = W < 1280 ? W : 1280;
    OW &= ~1u;
    unsigned OH = (unsigned)((double)H * OW / W) & ~1u;
    if (FAILED(MFStartup(MF_VERSION))) return 1;
    IMFAttributes* attrs = nullptr;
    MFCreateAttributes(&attrs, 1);
    attrs->SetUINT32(MF_READWRITE_ENABLE_HARDWARE_TRANSFORMS, TRUE);
    std::wstring tmp = std::wstring(argv[3]) + L".tmp.mp4";
    IMFSinkWriter* sink = nullptr;
    HRESULT hr = MFCreateSinkWriterFromURL(tmp.c_str(), nullptr, attrs, &sink);
    IMFMediaType* outT = nullptr; IMFMediaType* inT = nullptr;
    DWORD stream = 0;
    UINT32 num = b->FrameRate ? b->FrameRate : 30, den = b->FrameRateDiv ? b->FrameRateDiv : 1;
    if (SUCCEEDED(hr)) hr = MFCreateMediaType(&outT);
    if (SUCCEEDED(hr)) {
        outT->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
        outT->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_H264);
        outT->SetUINT32(MF_MT_AVG_BITRATE, 3500000);
        outT->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
        MFSetAttributeSize(outT, MF_MT_FRAME_SIZE, OW, OH);
        MFSetAttributeRatio(outT, MF_MT_FRAME_RATE, num, den);
        MFSetAttributeRatio(outT, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
        hr = sink->AddStream(outT, &stream);
    }
    if (SUCCEEDED(hr)) hr = MFCreateMediaType(&inT);
    if (SUCCEEDED(hr)) {
        inT->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
        inT->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_RGB32);
        inT->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
        inT->SetUINT32(MF_MT_DEFAULT_STRIDE, OW * 4);                // top row first
        MFSetAttributeSize(inT, MF_MT_FRAME_SIZE, OW, OH);
        MFSetAttributeRatio(inT, MF_MT_FRAME_RATE, num, den);
        MFSetAttributeRatio(inT, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
        hr = sink->SetInputMediaType(stream, inT, nullptr);
    }
    if (SUCCEEDED(hr)) hr = sink->BeginWriting();
    if (FAILED(hr)) { fwprintf(stderr, L"bink_to_mp4: the H.264 encoder would not start (0x%08x)\n", (unsigned)hr); close(b); return 1; }
    const LONGLONG dur = (LONGLONG)(10000000.0 * den / num);
    std::vector<unsigned char> scaled((size_t)OW * OH * 4);
    unsigned done = 0;
    for (unsigned i = 0; i < N && SUCCEEDED(hr); i++) {
        doframe(b);
        copy(b, frame.data(), (int)W * 4, H, 0, 0, SURFACE32 | COPYALL);
        if (i + 1 < N) next(b);
        shrink(frame.data(), W, H, scaled.data(), OW, OH);
        IMFMediaBuffer* buf = nullptr; IMFSample* smp = nullptr; BYTE* p = nullptr;
        hr = MFCreateMemoryBuffer((DWORD)scaled.size(), &buf);
        if (SUCCEEDED(hr)) hr = buf->Lock(&p, nullptr, nullptr);
        if (SUCCEEDED(hr)) { memcpy(p, scaled.data(), scaled.size()); buf->Unlock(); buf->SetCurrentLength((DWORD)scaled.size()); }
        if (SUCCEEDED(hr)) hr = MFCreateSample(&smp);
        if (SUCCEEDED(hr)) hr = smp->AddBuffer(buf);
        if (SUCCEEDED(hr)) { smp->SetSampleTime(dur * i); smp->SetSampleDuration(dur); hr = sink->WriteSample(stream, smp); }
        if (smp) smp->Release();
        if (buf) buf->Release();
        if (SUCCEEDED(hr)) done++;
        if (i % 300 == 0) printf("  frame %u of %u\n", i, N);
    }
    if (SUCCEEDED(hr)) hr = sink->Finalize();
    sink->Release(); outT->Release(); inT->Release(); attrs->Release();
    close(b);
    MFShutdown();
    if (FAILED(hr)) { DeleteFileW(tmp.c_str()); fwprintf(stderr, L"bink_to_mp4: encoding stopped (0x%08x)\n", (unsigned)hr); return 1; }
    MoveFileExW(tmp.c_str(), argv[3], MOVEFILE_REPLACE_EXISTING);
    printf("bink_to_mp4: %u frames, %u x %u -> %ls\n", done, OW, OH, argv[3]);
    return 0;
}
