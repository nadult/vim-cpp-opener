# vim-cpp-opener: Vim plugin for quick navigation of C++ projects

## Features
- Quickly open files by typing only part of the name which is unique to it
- Ability to quickly open .cpp and .h file side-by-side
- Doesn't display any kind of lists, file is opened immediately
 
## How to use

TODO: how to install  

Example usage (excerpt from .vimrc, using Vundle):
```
Plugin 'nadult/vim-cpp-opener' 
map <C-Z> :CppCloseFile<CR>
map <C-X> :CppOpenFile 
map <C-A> :CppGotoFile<CR>
```
TODO: write better description

## License

This plugin is licensed under Boost Software License. See license.txt .
