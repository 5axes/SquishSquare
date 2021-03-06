# Squish Square
Add element as Square Tab to test the leveling of your bed effect in print corner. 

![Square Tabs](./images/SquishSquare.png)

These Square Tab can be used to judge and adjust first layer squish especialy for difficult material like ABS.

The automatic functions of adding and deleting tabs make it easy to create each elements.

![Automatic Function](./images/buttons.png)

## Installation

#### Manually:
First, make sure your Cura version is  4.4 or newer.

Download or clone the repository into `[Cura configuration folder]/plugins/SquishSquare`.

The configuration folder can be found via **Help** -> **Show Configuration Folder** inside Cura.

This menu opens the following folder:
* Windows: `%APPDATA%\cura\<Cura version>\`, (usually `C:\Users\<your username>\AppData\Roaming\cura\<Cura version>\`)
* Mac OS: `$HOME/Library/Application Support/cura/<Cura version>/`
* Linux: `$HOME/.local/share/cura/<Cura version>/`


## How to use

- Load a model in Cura and select it
- Click on the "Squish Square" button on the left toolbar  (Shortcut D)
- Change de value for the tab *Size* in numeric input field in the tool panel if necessary

- Click anywhere on the model to place "Squish Square" in the lower corner of this model.

- **Clicking existing Tab deletes it**

- **Clicking existing Tab + Ctrl** switch automaticaly to the Translate Tool to modify the position of the "Squish Square".

The height of the tabs is automaticaly set according to the number of layer set in the menu . This height use the *Layer Height*  and the *Initial Layer Height* defined at the tab creation time.

>Note: it's easier to add/remove tabs when you are in "Solid View" mode


## Automatic Addition

![Automatic Addition](./images/addition.png)

Add automaticaly **two tabs** in the lower corner of every models present on the builtplate.

The first one is defined with the option Top/Bottom pattern to **concentric**.

![Top/Bottom pattern to concentric](./images/topbottomconcentric.png)

The second one is defined with the option Top/Bottom pattern to **lines**.

![Top/Bottom pattern to lines](./images/topbottomlines.png)


## Remove All / Last

Button to remove the lasts tab created ( **! but also every element defined as Squish Mesh !** )

![Remove All](./images/remove_all.png)

