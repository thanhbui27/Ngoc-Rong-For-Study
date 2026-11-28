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

Apply `wearable-titles.patch` after `reset-item-preview.patch`. This was also
applied directly to the local Unity project. It routes command -128 to wearable
effects (previously routed to the login parser), reads the fixed 13-byte title
payload, and clears the old title on unequip. Switching between effect-backed
accessories now removes the old effect before adding the new one.

The Java backend and this client patch must be deployed together for titles.
The Unity project is outside this repository; an existing distributed player
build requires a rebuild from these patched sources.
