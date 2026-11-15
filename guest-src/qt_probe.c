typedef struct _IO_FILE FILE;
extern FILE *stdout, *stderr;
extern void setbuf(FILE *, char *);
extern int puts(const char *);
extern int fprintf(FILE *, const char *, ...);
extern void *calloc(__SIZE_TYPE__, __SIZE_TYPE__);
extern void free(void *);
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern char *dlerror(void);
#define NULL ((void *)0)
#define RTLD_NOW 2
#define RTLD_GLOBAL 0x100

/* A small ABI probe for the exact Qt 5.5 binaries in this firmware. It does
 * not replace an application or claim to render a Qt Quick scene. */
int main(int argc, char **argv) {
    setbuf(stdout, NULL);
    puts("QT_PROBE_BEFORE_DLOPEN");
    void *gui = dlopen("libQt5Gui.so.5", RTLD_NOW | RTLD_GLOBAL);
    if (!gui) { fprintf(stderr, "Qt load: %s\n", dlerror()); return 1; }
    puts("QT_PROBE_LIBRARY_LOADED");
    typedef void (*ctor_t)(void *, int *, char **, int);
    typedef void (*dtor_t)(void *);
    ctor_t ctor = (ctor_t)dlsym(gui, "_ZN15QGuiApplicationC1ERiPPci");
    dtor_t dtor = (dtor_t)dlsym(gui, "_ZN15QGuiApplicationD1Ev");
    if (!ctor || !dtor) { fprintf(stderr, "Qt ABI: %s\n", dlerror()); return 2; }
    /* Qt stores state in its private allocation. This buffer deliberately
     * exceeds the public QObject/QGuiApplication instance size. */
    void *app = calloc(1, 65536);
    if (!app) return 3;
    puts("QT_PROBE_BEFORE_CONSTRUCTOR");
    ctor(app, &argc, argv, 0x050500);
    puts("QT_PROBE_APPLICATION_CREATED");
    dtor(app);
    free(app);
    puts("QT_PROBE_OK");
    return 0;
}

extern void __libc_start_main(int (*)(int, char **), int, char **,
                              void *, void *, void *, void *) __attribute__((noreturn));
__attribute__((used, noreturn)) void nac_start(long *stack) {
    __libc_start_main(main, (int)stack[0], (char **)(stack+1), NULL, NULL, NULL, stack);
}
__attribute__((naked, noreturn)) void _start(void) {
    __asm__ volatile("mov r0, sp\n" "b nac_start\n");
}
