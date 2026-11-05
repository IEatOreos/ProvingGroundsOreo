# Notices

Required Notice: Copyright 2026 the Project Proving Grounds contributors. Licensed under the PolyForm Noncommercial License
1.0.0 (LICENSE.md, https://polyformproject.org/licenses/noncommercial/1.0.0): free to use, share and change for any
noncommercial purpose; selling it, charging for access to it or earning money from it is not permitted.

## Halo and Microsoft

Halo: The Master Chief Collection © Microsoft Corporation. Project Proving Grounds was created under Microsoft's "Game
Content Usage Rules" using assets from Halo: The Master Chief Collection, and it is not endorsed by or affiliated with
Microsoft. Game Content Usage Rules: https://www.xbox.com/en-US/developers/rules

This project ships no game files, game code or art extracted from the games. Map data that comes from a game's
geometry (height maps, top-down pictures, glass masks, Forge piece shapes) is derived data, computed from each map's
level mesh, and is offered as a separate, optional map pack. Pictures from MCC's own menus are made on each
install from the user's own copy of the game.

## Third-party code

| Component | Where | License |
|---|---|---|
| Dear ImGui (Omar Cornut) | native/third_party/imgui | MIT, native/third_party/imgui/LICENSE.txt |
| MinHook (Tsuda Kageyu) | native/third_party/minhook | BSD 2-Clause, native/third_party/minhook/LICENSE.txt |
| Microsoft Edge WebView2 SDK (headers and static loader, for the app window native/ppg_window.exe) | native/third_party/webview2 | BSD 3-Clause style, native/third_party/webview2/LICENSE.txt |

These components keep their own licenses; the PolyForm Noncommercial terms cover this project's own code and data.

## The map tools (a separate program)

The 3D bots of the profile view, the armor effect sprites and some map data are made from each player's own game
files by bsp2obj.exe and model2obj.exe: [Proving Grounds Map Tools](https://github.com/AyoItzKye/proving-grounds-map-tools), a separate project under the GNU General Public
License v3.0, built on the Reclaimer map library (Gravemind2401 and contributors, GPL-3.0). The installer puts them in
tools\map_tools. This project only runs them as separate programs and contains none of their code; their source,
license and build steps are in their own repository.
