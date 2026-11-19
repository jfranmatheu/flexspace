# Changelog

What changed in each version of FlexSpace, newest first: new features, changes and fixes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 1.4.0

Requires Blender 5.3 or newer.

### Added

#### New widgets

- **Number Field**: a number drawn like Blender's own field, with its unit and small arrows. Drag to change it (`Shift` finer, `Ctrl` snaps to the step), click an arrow to step it, click to type a value.
- **Enum**: shows the items of an enum (or an integer with your own list of items) as segments or as a dropdown.
- **Set Value** mode for Toggles: on while the property has the chosen value, a click sets it.
- **Color Swatch**: shows a colour property the way Blender's colour fields do; a click opens Blender's colour picker.
- **Color Picker**: a colour wheel with a brightness bar, or a hue ring around a square (**Ring + Square**), with optional RGB, HSV and alpha sliders.
- **Color Palette**: a grid of swatches from its own list or a Blender palette; a click sets the colour.
- **Brush Picker**: activates a brush (Essentials, a library or the file) and shows when it is the active one, with its preview even before the brush is loaded. **Custom Roundness** makes it anything from square to a round brush button.
- **Ring Menu**: a round menu that lives on the canvas. Brushes in an outer ring, toggles and operators in an inner ring, the hovered item named in the middle, pages for more brushes. Fill the outer ring with every Essentials brush of a mode in one click. Items can look pressed (**On When**) or greyed out (**Disabled When**) from a property.
- **List**: a Blender collection as rows. Click to pick the active item, flip hide or lock, double-click to rename. Presets for Grease Pencil layers, material slots, UV maps, colour attributes, shape keys, vertex groups, bone collections and view layers.
- **Backdrop Image** (Add > Graphics): an image that sits below every widget, lets clicks through in Live Mode and can be locked, for a reference picture behind a picker or a panel.
- **Gaze (Eyes)** (Add > Data > Numbers): a 2D pad drawn as a pair of eyes that look where you drag. On a Rigify face rig it binds itself to the eye target. Any 2D pad can switch to **Look: Eyes**, and the **Rigify Gaze** button binds it.

#### Adding and editing widgets

- **Add Widget** panel on `Shift A`: start typing to search, pick a category on the left (Buttons, Data, Tools, Graphics, Layout, and Bone Picker in a picker), and click a card or press `Enter`. Data is split into Toggles, Choices, Numbers, Color, Text and Lists.
- An **Add** menu in the editor's header with the same categories, **Search...** and **From Property...**. Prefer the pie? Set **Add Menu** to **Pie** in the preferences.
- **From Property**: right-click any property in Blender and the right widget appears, already bound and labelled.
- **Copy and paste by content**: `Ctrl C` copies the selected widgets (groups, Flex Boxes and frames with what is inside), `Ctrl V` pastes them under the mouse. Paste as often as you like, into another canvas of the same kind or after opening another file. Also in the Selection and right-click menus.
- **Lineal slider**: `Shift` drags ten times finer, `Ctrl` snaps to the step, and `Ctrl`-click or a double-click lets you type the exact value.
- **Image Look** for every Image widget: opacity, saturation, brightness and a tint (Colorize or Multiply).
- Frames can be round (a circle around their members) and can hide their title.

#### Binding

- **Visible When** and **Disabled When** on every widget: show it only while a property is on, or grey it out. On a Frame, Flex Box or group they apply to everything inside.
- **Tooltips in Live Mode**: rest the mouse on a widget to see what it does: the operator and why it can't run, the script, the brush, or the bound property and its data path. Write your own in the new **Tooltip** field.
- **Broken bindings on the top bar**: Edit Mode counts the widgets with a broken binding (**⚠ 2 broken**) or none (**1 unbound**). Click the count to jump to the next one.
- **Animation state** on bound widgets in Blender's colours (animated, keyed, driven, changed). Over a widget in Live Mode, `I` inserts a keyframe, `Alt I` deletes it, `Shift Alt I` clears its keys and `Backspace` resets the value.
- **Pin an object**: a widget can drive one object instead of following the active one.
- The eyedropper now picks properties of any data (the scene, the world, a material, any data by name), enums and colours.

#### Canvas, layers and presets

- **Layers per mode and object**: each layer has a **Show When** rule (Always, Mode, Object, Object in Mode), and with **Switch Layers Automatically** the canvas shows the layer that fits when Blender's mode or the active object changes. A layer that doesn't fit is dimmed, with a button to enter its mode or select its object.
- **Global presets**: save a canvas as a preset and add it to any project. Linked canvases keep your local edits: **Overwrite**, **Sync** or **Unlink**, and **Restore Previous Version** brings back any of the last 5 versions.
- **Export and import** global presets as `.flexspace` files, and a **Shared Presets Folder** in the preferences for a team.
- **The canvas top bar** in Edit Mode: the canvas's preset and its state, the picker's armature, and the bindings that need you.
- **The Library** in the sidebar: global presets and the canvases of the file.

#### Armature Picker

- **Humanoid Body (Rigify)**: a full picker for a Rigify rig in one step (`Shift A` > Bone Picker): Adult Male or Adult Female, with Body, Hands, Feet and Face pages, IK/FK switches next to each IK hand and foot, and a **Hands & Feet View** option.
- **Character Backdrop** (on by default): each page is drawn over new character art (a male and a female body, hands, feet and face) as a locked backdrop, with the shapes traced from the drawings. **Hands Side** shows the backs of the hands or the palms.
- The **Face** page: every control of a Rigify face drawn on its feature of the female or male face, with an **Expressions** panel (a Gaze pad drawn as eyes, mouth pads and knobs) and the face bone collections. The Rigify demos have it too: copy it as a start for your own.

#### Demo files

- Demo files to open in a new Blender window, so your own file is never touched: Studio Control Panel, Viewport Shading Panel, Animation Controls, FlexSpace Studio (a layer per mode), Sculpt Wheel, Rigify Human Picker (with a Face tab on the face art), Simple Biped Picker, Rigify Male Body Picker, Rigify Female Body Picker and the new Rigify Character Picker (body, hands, feet and face over the character art).
- A demo browser over the editor (**Help > Demo Files**, or **Open a Demo** on an empty editor): categories, search and a card per demo. The demos are also listed in the preferences.

#### Docs

- The full documentation ships with the add-on as a web page: **Open Full Documentation** in the Help dialog. It has search, a table of contents, pictures and light and dark themes.

### Changed

- The use mode of a Flex Space canvas is now called **Live Mode**. The Armature Picker keeps Pose Mode.
- The canvas header is tidier: the theme is in **View > Theme**, the Selection Bar is in **View**, and a new **Help** menu holds Demo Files, Help and Report a Bug.
- The add-on preferences are named tabs: **Modules**, **Themes**, **Demo Files** and **Addon Settings**. The Modules tab lists the built-in modules; installing extra modules from a file is no longer offered.
- Switching between Edit Mode and Live Mode is no longer an undo step, and undo keeps the mode you are in.
- Faster drawing: widgets are no longer redrawn when unrelated data changes (posing, playback, edits elsewhere), and widgets outside the view are skipped.

### Fixed

- Copying a whole canvas (Make Single User, **Duplicate** in the Outliner, **File > Append**) keeps its layers, frames, groups and Flex Boxes, and the copy no longer shares state with the original.
- Undoing a change in Live Mode no longer switches the canvas back to Edit Mode.
- On a library-overridden rig, a widget bound to a property that can't be overridden shows **Not overridable** instead of writing a change that was lost on reload.
- A canvas recovers after an error while drawing, instead of failing on every redraw.
- The IK/FK puck updates the rig in the viewport right away.
- A 2D pad axis whose Min is higher than its Max no longer snaps to one end.
- Setting a widget's colour or value from a script no longer raises an error.
- Report a Bug shows the canvas name and fills in the issue form on GitHub.
- The spelling of **Assign Active Bone** in the interface.

## Earlier versions

Changes before 1.4.0 were not recorded in this file.
