# vim-cpp-opener: Quick navigation for C++ projects in Vim

## Features
- Instantly open (or goto if they are already opened) files by
  typing only part of the name which is unique to it
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

The easiest way to install it is through Vundle. Here is an example:
(excerpt from .vimrc, using Vundle):

```
Plugin 'nadult/vim-cpp-opener' 
map <C-Z> :CppCloseFile<CR>
map <C-X> :CppOpenFile 
map <C-A> :CppGotoFile<CR>
```

Now after pressing Ctrl+X and typing 'myclass' in hypothetical project,
the plugin will open MyClass.h and MyClass.cpp side by side.

TODO: write better description

## Additional info

For big projects with tens of thousands of files, search might become slow.
In that case you can restrict the plugin to search through selected directories.
This can be done by adding **.vim\_cpp\_project** file. Here is an example:
```
include/
src/
deps/sub_project1/
deps/sub_project2/

-build
-moc
```
This configuration file also contains some filters: all the files which contain
'build' or 'moc' in their full path name will be ignored.

## License

This plugin is licensed under Boost Software License. See license.txt .

## TODO

- Prioritize main file name over directory names (pages/aa, page.cpp; 'page' -> page.cpp)
