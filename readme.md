# vim-cpp-opener: Vim plugin for quick navigation of git-based C++ projects (mainly)

## Features
- Quickly open files by typing only part of the name which is unique to it
- Ability to open .cpp and .h file side-by-side
- Doesn't display any kind of lists, file is opened immediately


## How matching works

- Plugin uses git to find all files in current project
  (Plugin also works for projects which don't use git only not as well)

- First it tries to find a match within tracked files (within sub-modules as well)
  If no matches were found, it looks within untracked files
  If still no matches were found, then it looks within ignored files

- TODO: how matching & ranking works
 
## How to use

TODO: how to install  

Example usage (excerpt from .vimrc, using Vundle):

```
Plugin 'nadult/vim-cpp-opener' 
map <C-Z> :CppCloseFile<CR>
map <C-X> :CppOpenFile 
map <C-A> :CppGotoFile<CR>
```

Now after pressing Ctrl+X and typing 'myclass' in hypothetical project
plugin will open MyClass.h and MyClass.cpp side by side.

TODO: write better description

## License

This plugin is licensed under Boost Software License. See license.txt .
