/* Adapt Qt 5.5 minimalegl's null native window to a real Mesa pbuffer.
 * This library is opt-in through LD_PRELOAD inside the diagnostic guest. */
extern void *dlsym(void *, const char *);
extern int puts(const char *);
#define NEXT ((void *)-1)
#define NONE 0x3038

unsigned eglChooseConfig(void *display, const int *attributes, void **configs,
                         int size, int *count) {
    unsigned (*choose)(void *, const int *, void **, int, int *) =
        dlsym(NEXT, "eglChooseConfig");
    int adapted[257];
    int n = 0;
    if (!choose) return 0;
    if (attributes) {
        while (attributes[n] != NONE) {
            if (n >= 254) return 0;
            adapted[n] = attributes[n];
            adapted[n+1] = attributes[n+1];
            if (adapted[n] == 0x3033 && (adapted[n+1] & 4))
                adapted[n+1] = (adapted[n+1] & ~4) | 1;
            n += 2;
        }
        adapted[n] = NONE;
    }
    return choose(display, attributes ? adapted : attributes, configs, size, count);
}

void *eglCreateWindowSurface(void *display, void *config, void *window, const int *attributes) {
    (void)attributes;
    /* Only minimalegl's absent native window is supported. */
    if (window) return (void *)0;
    void *(*create)(void *, void *, const int *) = dlsym(NEXT, "eglCreatePbufferSurface");
    const int size[] = {0x3057,800,0x3056,480,NONE};
    void *surface = create ? create(display, config, size) : (void *)0;
    if (surface) puts("NAC_QT_PBUFFER_CREATED=800x480");
    return surface;
}
