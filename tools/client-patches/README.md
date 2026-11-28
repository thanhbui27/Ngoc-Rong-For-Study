# Unity item preview fix

Applied locally to `D:/Code/game nro/NroHihi/Assets/Scripts/Char.cs`.
The client is outside this Git repository, so `reset-item-preview.patch` carries
the Char/Controller changes for other Unity checkouts. Apply from the Unity project root using
`git apply /path/to/reset-item-preview.patch` (or apply the diff manually).

Each preview starts from the captured equipped appearance. Missing slots restore
that base, including an empty bag (`-1`), and closing the panel restores every slot.
This prevents a partial/unconfigured item from inheriting the previous preview.

Copy `ItemPreviewRegressionCheck.cs` into `Assets/Editor` and select **Tools / NRO / Check item preview isolation**. The result is
written to `%TEMP%/nro-item-identity/preview-regression.json`. All five passed in Unity
2022.3.62f2 on 2026-11-28. The editor helper is not included in player builds.


## Wearable titles and back effects (V30)

Apply `wearable-titles.patch` after `reset-item-preview.patch`. This is also
applied directly to the local Unity project. `Controller2.readInfoEffChar` already
handles command -128; the primary controller must not consume it again.
The backend sends one 12-byte add payload and a targeted 7-byte remove payload.
Removing a title no longer clears all character effects. Back-accessory changes
remove only the previous bag effect, preserving titles in the 201–254 ID range.

The Unity project is outside this repository; an existing distributed player
build requires a rebuild from these patched sources.
