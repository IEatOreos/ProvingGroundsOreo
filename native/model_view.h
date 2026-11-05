// model_view.h: the Settings tab's 3D bot view: a character model (native/bin/models/<name>.mdl, tools/model_pack.py)
// drawn with its armor pieces and colours into a texture the panel shows with ImGui.
#pragma once

struct mv_pick { const char* region; const char* perm; };   // the piece worn on a region: a permutation name, or
                                                            // "#<n>" its index in the model's list for that region
// armor: the primary colour; secondary: Halo 3's second colour (the textured models' colour-change green channel)
// visor_rim: a visor's colour toward its edges (Halo 4's visors have a front and a rim colour), used when rim_on
struct mv_colors { float armor[3], undersuit[3], visor[3], lights[3], skin[3], secondary[3], visor_rim[3]; bool rim_on; };

// Draws the model into this view's own render target (made or resized on demand) and returns it as an
// ImTextureID (an ID3D11ShaderResourceView*), 0 when the model file or the device is missing. yaw: the turntable
// angle (radians, 0 = facing the viewer). device / context: ID3D11Device*, ID3D11DeviceContext*. The game's
// graphics state is saved and put back around the draw.
unsigned long long mv_render(void* device, void* context, const wchar_t* model_path, const mv_pick* picks, int npicks,
                             const mv_colors& colors, float yaw, int width, int height);
// Whether a region has a permutation of that name in the model (the panel's fallbacks); false if the model is missing
bool mv_has(void* device, const wchar_t* model_path, const char* region, const char* perm);
// How close the next mv_render frames the figure: 0 the whole figure, 1 its upper torso (head to the waist, Halo 3's
// armory view), in between a zoom from one to the other
void mv_set_zoom(float zoom);
// Extra room above the head in the next mv_render's frame, a share of the framed height (0 none): an armor effect's
// fire, hearts or storm cloud above it stay in the picture
void mv_set_headroom(float share);
// Where the last mv_render drew the head (its worn head and helmet pieces): out[0], out[1] its centre in the view's
// pixels, out[2] its half height in pixels (0 before any draw). The panel's armor effects sit on it.
void mv_head(float out[3]);
