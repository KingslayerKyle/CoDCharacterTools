# CoDCharacterTools
## Description
Various utilities to automate the process of porting CoD > T7 playable character models for use with Bo3 Mod Tools.

I have not tested outside of Maya 2018, as this is the version i'm using.

Different versions may or may not work, if you find any issues feel free to open a PR.

I have included a few example rigs for BO4 and Cold War.

If you create any of your own, use the same naming convention for the files as the plugin is dependant on it

## Requirements
- [CoDMayaTools](https://github.com/LunaRyuko/CoDMayaTools/releases)
- [SETools](https://github.com/dtzxporter/SETools)

## Installation
- Place the files from this repository along with the files from the requirements above in `Documents\maya\version\scripts`

- That's it. Feel free to use the userSetup.mel that I have provided or you can add the contents of it to your own.

## Usage
- [Click here for example](https://www.youtube.com/watch?v=po5V1ngRqjQ)

- **Only SEModel format is supported**

- Import your model, if your model comes in parts then import all of them to the scene

- Using the menu you can choose the "Convert from" option, and select the type of model you're converting

- After this, you can choose an animation to test your model with. This is much more convenient than launching the game every time you want to test a model (animations not provided)

- To add animations to the menu, add the SEAnim files to `Documents\maya\version\scripts\CoDCharacterTools\Animations`

- I would recommend adding animations for testing fullbody and some viewmodel reload animations for testing viewhands

## Support
If you're feeling generous, consider supporting me with the link below...

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/kingslayerkyle)

## Note
If you use this, please credit me for it along with the people in the list below.

# Credits
Luna Ryuko\
Scobalula\
Aidian Shafran\
DTZxPorter\
SE2Dev\
ThomasCat
