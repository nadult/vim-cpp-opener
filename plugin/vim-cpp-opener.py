# Copyright (C) Krzysztof Jakubowski <nadult@fastmail.fm>
# This file is part of CppOpener. See license.txt for details.

import vim
import sys
import re
import os
import glob

# TODO: open only single cpp file
# TODO: case insensitive as lower priority
# TODO: jump to line directly
# TODO: better way to find project dir
# TODO: better filtering (for cmake projects as well)
# TODO: optional customization file, which will:
# TODO: configuring file extensions
#  inform about where root dir is
#  specify matched files
#  specify filtered dirs

# TODO: when opening two files, do it only if file name is the same

def extractFileLine(buf, cursor):
    line = buf[cursor[0] - 1]

    str_end = len(line)
    for i in range(cursor[1], len(line)):
        if line[i] == '>' or line[i] == '"':
            str_end = i
            break
    
    str_start = 0
    for i in range(cursor[1], 0, -1):
        if line[i] == '<' or line[i] == '"':
            str_start = i + 1
            break

    out = line[str_start:str_end]
    for c in out:
        if not(str.isalnum(c) or c == '_' or c == '.' or c == '/' or c == ':'):
            return None

    parts = out.split(":")

    if len(parts) > 2 or (len(parts) == 1 and len(parts[0]) == 0):
        return None
    if len(parts) == 1:
        return [parts[0], ""]
    return parts

def testFilePath(file_path):
    if os.path.isfile(file_path):
        return True
    for buf in vim.buffers:
        if buf.name == file_path:
            print("Buffer: " + file_path)
            return True

    return False

def getFileContents(file_path):
    contents = []

    for buf in vim.buffers:
        if buf.name == file_path:
            contents = "\n".join(buf)
            break
    
    if not contents:
        try:
            contents = open(file_path, 'r').read()
        except Exception as err:
            pass

    return contents

def getLineColumn(file_contents, tag_name):
    lines = file_contents.split("\n")
    pattern = "name=\"" + tag_name + "\""

    column = 0
    line = 0
    for l in range(0, len(lines)):
        column = lines[l].find(pattern)
        if column != -1:
            line = l
            break
    return (line + 1, column + 7)

def findFilePath(current_path, file_path):
    current_path = os.path.abspath(current_path)

    if os.path.isfile(current_path):
        current_path = os.path.split(current_path)[0]

    for i in range(0, 10):
        tmp_path = os.path.abspath(current_path + '/' + file_path)
        if testFilePath(tmp_path):
            return tmp_path
        dir_up = os.path.abspath(os.path.join(current_path, os.pardir))
        if dir_up == current_path:
            return None
        current_path = dir_up

def isFileOpened(file_name):
    filepath = os.path.realpath(file_name)
    for tab in vim.tabpages:
        for win in tab.windows:
            if win.buffer.name == filepath:
                return True
    return False

# source: YouCompleteMe
def tryJumpLocationInOpenedTab(file_name, line = None, column = None):
    filepath = os.path.realpath(file_name)

    for tab in vim.tabpages:
        for win in tab.windows:
            if win.buffer.name == filepath:
                vim.current.tabpage = tab
                vim.current.window = win
                if line and column:
                    vim.current.window.cursor = ( line, column - 1 )

                # Center the screen on the jumped-to location
                vim.command( 'normal! zz' )
                return True
    return False

def gotoFile(file_path, line, column):
    if tryJumpLocationInOpenedTab(file_path, line, column):
        return
    vim.command("tabedit " + file_path)
    tryJumpLocationInOpenedTab(file_path, line, column)

project_dir = None
system_includes = None

def findProjectDir_():
    pdir = os.path.abspath('.');
    home_dir = os.path.abspath(os.path.expanduser("~"))

    maybe_dir = pdir

    while True:
        if os.path.isfile(os.path.join(pdir, "Makefile")):
            maybe_dir = pdir
        if os.path.isdir(os.path.join(pdir, ".git")):
            return pdir
        if os.path.isfile(os.path.join(pdir, ".ycm_extra_conf.py")):
            return pdir

        next_dir = os.path.abspath(os.path.join(pdir, ".."))
        if os.path.ismount(next_dir) or next_dir == home_dir or next_dir == pdir:
            break
        pdir = next_dir

    return maybe_dir

def findProjectDir():
    global project_dir
    project_dir = findProjectDir_()

def extractSystemIncludes(flags):
    out = []
    for i in range(len(flags)):
        if flags[i] == "-isystem" and i+1 < len(flags):
            out.append(flags[i + 1])
    return out

def loadYCMScript():
    global project_dir
    global system_includes
    ycm_path = os.path.join(os.path.abspath(project_dir), ".ycm_extra_conf.py")
    slocals = dict()
    exec(open(ycm_path).read(), dict(), slocals)
    system_includes = extractSystemIncludes(slocals["flags"])


def fullListing(cur_dir):
    out = []
    files = []
    extensions = [".cpp", ".c", ".h", ".hpp", ".cxx", ".wiki", ".py", ".txt", ".shader", ".vim", ".xml", ".md", ".toml", ".scss"]
    
    for dirpath, dirnames, filenames in os.walk(cur_dir, followlinks=True):
        if dirpath.endswith(".git"): 
            continue
            
        for f in filenames:
            [name, ext] = os.path.splitext(f)
            if  ext in extensions or name.startswith("Makefile"):
                file_name = os.path.join(dirpath, f)
                if file_name.startswith("./"):
                    file_name = file_name[2:]
                files.append(file_name)
                
    if len(files) > 0:
        out.append((cur_dir, files))
    return out

def matchFiles(pattern, files):
    out = []
    for (fdir, files) in files:
        for ffile in files:
            path = os.path.join(fdir, ffile)
            if pattern in path:
                out.append(os.path.abspath(path))
    return out

def openCppFile(file_path, split):
    if vim.current.window.width < 140:
        split = False
    cmd = "vsplit " if split else "tabnew "
    if not tryJumpLocationInOpenedTab(file_path):
        vim.command(cmd + file_path)

def rankMatching(fpath, pattern):
    base_name = os.path.basename(fpath)
    if base_name == pattern:
        return 0

    (bname, bext) = os.path.splitext(base_name)
    if bname == pattern:
        return 1
    if pattern in bname:
        return 2
    return 3

def filterBestMatches(flist, pattern):
    if len(flist) == 0:
        return []

    pattern = os.path.basename(pattern)
    ranks = []
    best_rank = 9999
    for fpath in flist:
        rank = rankMatching(fpath, pattern)
        ranks.append((rank, fpath))
        best_rank = min(best_rank, rank)

    out = []
    for (rank, fpath) in ranks:
        if(rank == best_rank):
            out.append(fpath)
    return out

def filterLinks(flist):
    fset = set()
    for fpath in flist:
        fset.add(os.path.realpath(fpath))
    flist = []
    for fpath in fset:
        flist.append(fpath)
    return flist

def compatibleExt(ext1, ext2):
    for n in [1,2]:
        if ext1 == ".h" and (ext2 == ".c" or ext2 == ".cpp" or ext2 == ".cxx"):
            return True
        if ext1 == ".hpp" and (ext2 == ".cpp" or ext2 == ".cxx"):
            return True
        (ext1, ext2) = (ext2, ext1)
    return False

def findSuitableOpenedFiles(file_name):
    base_name = os.path.basename(file_name)
    (bname, bext) = os.path.splitext(base_name)

    result = []
    for t in vim.tabpages:
        for w in t.windows:
            pair_name = os.path.basename(w.buffer.name)
            (pname, pext) = os.path.splitext(pair_name)
            if bname == pname and compatibleExt(bext, pext):
                result.append(w.buffer.name)
    return result

def filterLinks(files):
    fset = set()
    for felem in files:
        fset.add(os.path.realpath(felem))
    fout = []
    for felem in fset:
        fout.append(felem)
    return fout

def openCppFiles(pattern, only_best = False):
    global project_dir

    all_files = fullListing(project_dir)
    flist = matchFiles(pattern, all_files)
    flist = filterLinks(flist)

    if len(flist) >= 2 or only_best:
        best_list = filterBestMatches(flist, pattern)
        best_list = filterLinks(best_list)
        if len(best_list) > 0:
            flist = best_list

    if len(flist) == 0:
        print("No cpp files found matching pattern: " + pattern)
    elif len(flist) == 1:
        suitable_pairs = findSuitableOpenedFiles(flist[0])
        if len(suitable_pairs) == 1:
            tryJumpLocationInOpenedTab(suitable_pairs[0])
        openCppFile(flist[0], len(vim.windows) == 1)
    elif len(flist) == 2:
        if flist[0].endswith(".h"):
            (flist[0], flist[1]) = (flist[1], flist[0])
        if isFileOpened(flist[1]):
            tryJumpLocationInOpenedTab(flist[1])
            openCppFile(flist[0], True)
        else:
            openCppFile(flist[0], False)
            openCppFile(flist[1], True)
    else:
        if len(flist) > 20:
            flist = flist[0:20]
            flist.append("...")
        print("Too many files found: " + str(flist))

def closeFiles():
    num_windows = len(vim.windows)
    for n in range(num_windows):
        vim.command("q")

if __name__ == "__main__":
    findProjectDir()
    #loadYCMScript()

    if sys.argv[0] == "open_file":
        openCppFiles(sys.argv[1])
    elif sys.argv[0] == "close_file":
        closeFiles()
    elif sys.argv[0] == "goto_file":
        file_line = extractFileLine(vim.current.buffer, vim.current.window.cursor)
        if file_line is not None:
            openCppFiles(file_line[0], only_best=True)
        else:
            print("Invalid target")
    else:
        print("Invalid command: " + str(sys.argv));
