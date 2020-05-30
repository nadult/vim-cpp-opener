" Copyright (C) Krzysztof Jakubowski <nadult@fastmail.fm>
" This file is part of CppOpener. See license.txt for details.

if !has('python3')
	echoerr "Python 3 unavailable"
	finish
endif

let g:cppopener_script = ((fnamemodify(resolve(expand('<sfile>:p')), ':h')).'/vim-cpp-opener.py')

function! RunCppOpener(args)
	let s:cppopener_args   = a:args
	py3 import vim
	py3 sys.argv = vim.eval("s:cppopener_args").split()
	execute 'py3file' . g:cppopener_script
endfunc

command! -nargs=1 CppOpenFile call RunCppOpener("open_file <args>")
command! CppCloseFile call RunCppOpener("close_file")
command! CppGotoFile call RunCppOpener("goto_file")
