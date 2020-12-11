# Copyright (C) Krzysztof Jakubowski <nadult@fastmail.fm>
# This file is part of CppOpener. See license.txt for details.

import vim, sys, re, os, glob, time, subprocess, mimetypes

enable_logging = False

def logFunc(name, start_time, params):
    if enable_logging:
        run_time = time.time() - start_time
        print("{} time:{}".format(name, run_time))
        for (key, value) in params:
            print("  {} = {}".format(key, value))

# TODO: better name!
# TODO: show file selector menu when too many files matched
# TODO: jump to line directly
# TODO: quick way to open directory ?
# TODO: better way to find project dir
# TODO: inform about where root dir is?
# TODO: better handling of modified buffers when closing
# TODO: when opening two files, do it only if base file name is the same?

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

prio_extensions = [".cpp", ".cc", ".c", ".h", ".hpp", ".cxx", ".java", ".m", ".mm", ".wiki", ".py", ".txt", ".shader", ".vim", ".xml", ".md", ".json"]
prio_regex = re.compile(r'({})$'.format( '|'.join(re.escape(x) for x in prio_extensions) ))

def getProjectsFromConfig(path):
    confPath = os.path.join(path, ".vim_cpp_project")
    if os.path.isfile(confPath):
        with open(confPath) as file:
            project_dirs = []
            project_filters = []
            for x in file.readlines():
                x = x.strip()
                if x.startswith("-"):
                    project_filters.append(x[1:])
                elif x:
                    project_dirs.append(os.path.abspath(os.path.join(path, x)))
            return project_dirs, project_filters
    return ([], [])

# What if we're opened in home directory or even root ?
def findProjectDirs_():
    pdir = os.path.abspath('.');
    home_dir = os.path.abspath(os.path.expanduser("~"))
    maybe_dir = pdir

    while True:
        if(os.path.isfile(os.path.join(pdir, "Makefile")) or
         os.path.isfile(os.path.join(pdir, "CMakeLists.txt")) or
         os.path.isfile(os.path.join(pdir, ".ycm_extra_conf.py")) or
         os.path.isdir(os.path.join(pdir, ".git"))):
            maybe_dir = pdir

        confProjects, confFilters = getProjectsFromConfig(pdir)
        if confProjects or confFilters:
            return (confProjects, confFilters)

        next_dir = os.path.abspath(os.path.join(pdir, ".."))
        if os.path.ismount(next_dir) or next_dir == home_dir or next_dir == pdir:
            break
        pdir = next_dir

    return ([maybe_dir], [])

def isGitProject(path):
    return os.path.isdir(os.path.join(path, ".git"))

def findProjectDirs():
    start_time = time.time()
    project_dirs, project_filters = findProjectDirs_()
    git_dirs = list(filter(isGitProject, project_dirs))
    logFunc("findProjectDir", start_time, [("dirs", project_dirs), ("filter", project_filters), ("git_dirs", git_dirs)])
    return project_dirs, project_filters

def extractSystemIncludes(flags):
    out = []
    for i in range(len(flags)):
        if flags[i] == "-isystem" and i+1 < len(flags):
            out.append(flags[i + 1])
    return out

def fullListing(cur_dir):
    start_time = time.time()
    files = []
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(cur_dir, followlinks=True):
        count += len(filenames)
        for f in filenames:
            file_name = os.path.join(dirpath, f)
            if file_name.startswith("./"):
                file_name = file_name[2:]
            files.append(file_name)

    logFunc("fullListing", start_time, [('count', count)])
    return files

def filterSubmoduleForeach(prefix, lines):
    cur_prefix = prefix + "/"
    out = []

    for line in lines:
        if line.startswith("Entering '"):
            cur_prefix = os.path.join(prefix, line[10:-1]) + "/"
        else:
            out.append(cur_prefix + line)
    return out


# Returns list of files in git repository.
# 3 modes are supported: tracked, untracked, ignored
def gitListing(cur_dir, mode="tracked"):
    start_time = time.time()

    cmd_untracked = "git ls-files --others --exclude-standard"
    cmd_ignored   = "git ls-files --others --exclude-standard --ignored"

    cmd_untracked = '{}; git submodule foreach --recursive "{}"'.format(cmd_untracked, cmd_untracked)
    cmd_tracked   = 'git ls-files --recurse-submodules'
    cmd_ignored   = '{}; git submodule foreach --recursive "{}"'.format(cmd_ignored, cmd_ignored)

    cmd = (cmd_tracked if (mode == "tracked") else
          (cmd_untracked if (mode == "untracked") else cmd_ignored));
        
    prev_dir = os.getcwd()
    os.chdir(cur_dir)

    stream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result = stream.stdout.read().decode("utf-8").splitlines()
    if mode != "tracked":
        result = filterSubmoduleForeach(cur_dir, result)
    
    os.chdir(prev_dir)

    logFunc("gitListing", start_time,
            [('cur_dir', cur_dir),
             ('mode', mode),
             ('count', len(result))])
    return result

def matchFiles(pattern, proj_dir, files):
    start_time = time.time()
    pattern = pattern.lower()
    out = []
    for ffile in files:
        path = os.path.join(proj_dir, ffile)
        if pattern in path.lower():
            out.append(os.path.abspath(path))

    logFunc("matchFiles", start_time, [('num_matched', len(out))])
    return out

def openCppFile(file_path, split):
    if vim.current.window.width < 140:
        split = False
    cmd = "vsplit " if split else "tabnew "
    if not tryJumpLocationInOpenedTab(file_path):
        vim.command(cmd + file_path)

def isTextFile(file_path):
    if not os.path.isfile(file_path):
        return False
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return not is_binary_string(open(file_path, 'rb').read(1024))

worst_rank = 9999

def rankMatching(file_path, pattern):
    lo_pattern = pattern.lower()

    file_name = os.path.basename(file_path)
    if file_name == pattern:
        return 0
    if file_name.lower() == lo_pattern:
        return 10

    (base, ext) = os.path.splitext(file_name)

    if pattern == base:
        return 20
    if lo_pattern == base.lower():
        return 30

    if pattern in base:
        return 40
    if lo_pattern in base.lower():
        return 50

    if pattern in file_name:
        return 60
    if lo_pattern in file_name.lower():
        return 70

    return worst_rank

def filterBestMatches(files, pattern):
    if len(files) == 0:
        return []

    pattern = os.path.basename(pattern)
    ranked_files = []

    best_rank = worst_rank
    for fpath in files:
        rank = rankMatching(fpath, pattern)
        if rank == worst_rank or not isTextFile(fpath):
            continue

        # Some extensions have higher priority than others
        if not bool(prio_regex.search(fpath)):
            rank += 5

        ranked_files.append((rank, fpath))
        best_rank = min(best_rank, rank)

    if enable_logging:
        ranked_files.sort()
        for rank, path in ranked_files:
            print("Rank '{}': {}".format(path, rank))

    out = []
    for (rank, fpath) in ranked_files:
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


def findCppFiles(project_dir, pattern, only_best = False):
    is_git_project = isGitProject(project_dir)
    files = gitListing(project_dir, "tracked") if is_git_project else fullListing(project_dir)
    files = filterLinks(matchFiles(pattern, project_dir, files))

    if len(files) == 0 and is_git_project:
        files = gitListing(project_dir, "untracked")
        files = filterLinks(matchFiles(pattern, project_dir, files))
    if len(files) == 0 and is_git_project:
        files = gitListing(project_dir, "ignored")
        files = filterLinks(matchFiles(pattern, project_dir, files))
    return files

def isNotFiltered(project_filters, item):
    for filt in project_filters:
        if filt in item:
            return False
    return True

def openCppFiles(project_dirs, project_filters, pattern, only_best = False):
    files = []
    for project_dir in project_dirs:
        files.extend(findCppFiles(project_dir, pattern, only_best))

    files = [file for file in files if isNotFiltered(project_filters, file)]

    if len(files) >= 2 or only_best:
        best_list = filterBestMatches(files, pattern)
        best_list = filterLinks(best_list)
        if len(best_list) > 0:
            files = best_list

    if len(files) == 0:
        print("No cpp files found matching pattern: " + pattern)
        return
    elif len(files) == 1:
        suitable_pairs = findSuitableOpenedFiles(files[0])
        if len(suitable_pairs) == 1:
            tryJumpLocationInOpenedTab(suitable_pairs[0])
        openCppFile(files[0], len(vim.windows) == 1)
    elif len(files) == 2:
        if files[0].endswith(".h"):
            (files[0], files[1]) = (files[1], files[0])
        if isFileOpened(files[1]):
            tryJumpLocationInOpenedTab(files[1])
            openCppFile(files[0], True)
        else:
            openCppFile(files[0], False)
            openCppFile(files[1], True)
    else:
        if len(files) > 40:
            files = files[0:40]
            files.append("...")
        print("Too many files found: " + str(files))

def closeFiles():
    num_windows = len(vim.windows)
    for n in range(num_windows):
        vim.command("q")

if __name__ == "__main__":
    project_dirs, project_filters = findProjectDirs()

    if sys.argv[0] == "open_file":
        openCppFiles(project_dirs, project_filters, sys.argv[1])
    elif sys.argv[0] == "close_file":
        closeFiles()
    elif sys.argv[0] == "goto_file":
        file_line = extractFileLine(vim.current.buffer, vim.current.window.cursor)
        if file_line is not None:
            openCppFiles(project_dirs, project_filters, file_line[0], only_best=True)
        else:
            print("Invalid target")
    else:
        print("Invalid command: " + str(sys.argv));
