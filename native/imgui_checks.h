// imgui_checks.h (custom, Nov 12): botcore.dll's Dear ImGui configuration (build.bat /DIMGUI_USER_CONFIG). A failed
// ImGui check (IM_ASSERT) is written to the botcore log (overlay.cpp hb_imgui_assert), once a place, instead of the C
// runtime's assert: its dialog closed MCC with no crash report or log line (live Nov 11, the BOTS panel's Remove all).
// The tests and the preview builds keep ImGui's own assert.
#pragma once
void hb_imgui_assert(const char* expr, const char* file, int line);
#define IM_ASSERT(_EXPR) ((_EXPR) ? (void)0 : hb_imgui_assert(#_EXPR, __FILE__, __LINE__))
