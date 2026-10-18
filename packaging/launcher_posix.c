#define _POSIX_C_SOURCE 200809L
#include <libgen.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char path[PATH_MAX];
    ssize_t length = readlink("/proc/self/exe", path, sizeof path - 1);
    if (length < 0) {
        fprintf(stderr, "Der Pfad des Programms fehlt.\n");
        return 127;
    }
    path[length] = 0;
    char dirbuf[PATH_MAX];
    snprintf(dirbuf, sizeof dirbuf, "%s", path);
    char *dir = dirname(dirbuf);
    char script[PATH_MAX];
    char bundled[PATH_MAX];
    snprintf(script, sizeof script, "%s/shatuide.py", dir);
    snprintf(bundled, sizeof bundled, "%s/python/bin/python3", dir);
    if (chdir(dir) != 0) {
        fprintf(stderr, "Der Programmordner laesst sich nicht oeffnen.\n");
        return 127;
    }
    if (access(script, R_OK) != 0) {
        fprintf(stderr, "shatuide.py liegt nicht neben dem Programm.\n");
        return 1;
    }
    char **args = calloc((size_t)argc + 2, sizeof(char *));
    if (!args) {
        return 127;
    }
    args[1] = script;
    for (int index = 1; index < argc; index += 1) {
        args[index + 1] = argv[index];
    }
    if (access(bundled, X_OK) == 0) {
        args[0] = bundled;
        execv(bundled, args);
    }
    args[0] = "python3";
    execvp("python3", args);
    args[0] = "python";
    execvp("python", args);
    fprintf(stderr, "Python 3 nicht gefunden.\n");
    free(args);
    return 127;
}
