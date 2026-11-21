/* Adapt Qt 5.5 minimalegl's null native window to a real Mesa pbuffer.
 * This library is opt-in through LD_PRELOAD inside the diagnostic guest. */
extern void *dlsym(void *, const char *);
typedef struct _IO_FILE FILE;
extern FILE *stderr;
extern char *getenv(const char *);
extern void *calloc(__SIZE_TYPE__, __SIZE_TYPE__);
extern int strncmp(const char *, const char *, __SIZE_TYPE__);
extern void free(void *);
extern FILE *fopen(const char *, const char *);
extern int fprintf(FILE *, const char *, ...);
extern int snprintf(char *, __SIZE_TYPE__, const char *, ...);
extern __SIZE_TYPE__ fwrite(const void *, __SIZE_TYPE__, __SIZE_TYPE__, FILE *);
extern int fclose(FILE *);
extern int rename(const char *, const char *);
extern int unlink(const char *);
#define NEXT ((void *)-1)
#define NONE 0x3038

/* This firmware's fontconfig code dereferences the QPA native interface for
 * default hinting. The minimalegl integration returns null. Use Qt 5.5's own
 * default interface object, whose native resource methods return no resource.
 * Its implicit constructor is QObject construction followed by a vptr store
 * on the firmware's 32-bit ARM C++ ABI. */
static void *native_interface_storage[16];
static void *native_interface_fallback;
static int native_interface_once;

static void initialize_native_interface(void) {
    void (*construct_qobject)(void *,void *)=dlsym(NEXT,"_ZN7QObjectC1EPS_");
    void **vtable=dlsym(NEXT,"_ZTV24QPlatformNativeInterface");
    void *screen_resource=dlsym(NEXT,"_ZN24QPlatformNativeInterface23nativeResourceForScreenERK10QByteArrayP7QScreen");
    if (!construct_qobject || !vtable || !screen_resource || vtable[2+14]!=screen_resource)
        return;
    construct_qobject(native_interface_storage,(void *)0);
    native_interface_storage[0]=vtable+2;
    native_interface_fallback=native_interface_storage;
    fprintf(stderr,"NAC_QT_NATIVE_INTERFACE_FALLBACK\n");
}

void *_ZN15QGuiApplication23platformNativeInterfaceEv(void) {
    void *(*native_interface)(void)=dlsym(NEXT,"_ZN15QGuiApplication23platformNativeInterfaceEv");
    void *result=native_interface ? native_interface() : (void *)0;
    if (!result && getenv("NAC_QT_NATIVE_INTERFACE_FALLBACK")) {
        int (*once)(int *,void (*)(void))=dlsym(NEXT,"pthread_once");
        if (once) once(&native_interface_once,initialize_native_interface);
        result=native_interface_fallback;
    }
    return result;
}

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
    if (surface) fprintf(stderr,"NAC_QT_PBUFFER_CREATED=800x480\n");
    return surface;
}

/* Opt-in readback of the real presentation surface. Capture the first few swaps,
 * then every thirtieth swap, and publish complete files by atomic rename.
 * The adapter supports the existing 800x480 diagnostic pbuffer profile only. */
static void capture_surface(void *display, void *surface, const char *path) {
    unsigned (*query)(void *,void *,int,int *)=dlsym(NEXT,"eglQuerySurface");
    void *(*current_surface)(int)=dlsym(NEXT,"eglGetCurrentSurface");
    void (*read_pixels)(int,int,int,int,unsigned,unsigned,void *)=dlsym(NEXT,"glReadPixels");
    void (*get_integer)(unsigned,int *)=dlsym(NEXT,"glGetIntegerv");
    void (*bind_framebuffer)(unsigned,unsigned)=dlsym(NEXT,"glBindFramebuffer");
    void (*bind_buffer)(unsigned,unsigned)=dlsym(NEXT,"glBindBuffer");
    void (*pixel_store)(unsigned,int)=dlsym(NEXT,"glPixelStorei");
    const unsigned char *(*get_string)(unsigned)=dlsym(NEXT,"glGetString");
    int width=0,height=0;
    if (!query || !current_surface || current_surface(0x3059)!=surface ||
        !read_pixels || !get_integer || !bind_framebuffer || !bind_buffer ||
        !pixel_store || !get_string ||
        !query(display,surface,0x3057,&width) || !query(display,surface,0x3056,&height) ||
        width!=800 || height!=480) return;
    char temporary[512];
    int length=snprintf(temporary,sizeof(temporary),"%s.part",path);
    if (length<0 || length>=(int)sizeof(temporary)) return;
    const char *version=(const char *)get_string(0x1f02);
    if (!version || strncmp(version,"OpenGL ES ",10)!=0) return;
    int es3=version[10]>='3' && version[10]<='9';
    unsigned char *pixels=calloc(800*480,4);
    if (!pixels) return;
    int framebuffer=0,alignment=4,pack_buffer=0,row_length=0,skip_rows=0,skip_pixels=0;
    unsigned read_target=es3 ? 0x8ca8 : 0x8d40;
    get_integer(es3 ? 0x8caa : 0x8ca6,&framebuffer);
    bind_framebuffer(read_target,0);
    get_integer(0x0d05,&alignment);
    pixel_store(0x0d05,4);
    if (es3) {
        get_integer(0x88ed,&pack_buffer);
        bind_buffer(0x88eb,0);
        get_integer(0x0d02,&row_length);get_integer(0x0d03,&skip_rows);get_integer(0x0d04,&skip_pixels);
        pixel_store(0x0d02,0);pixel_store(0x0d03,0);pixel_store(0x0d04,0);
    }
    /* Read the surface being presented; preserve the caller's framebuffer and
     * pixel-pack state, including separate read/draw framebuffers in GLES3. */
    read_pixels(0,0,800,480,0x1908,0x1401,pixels);
    if (es3) {
        bind_buffer(0x88eb,(unsigned)pack_buffer);
        pixel_store(0x0d02,row_length);pixel_store(0x0d03,skip_rows);pixel_store(0x0d04,skip_pixels);
    }
    pixel_store(0x0d05,alignment);
    bind_framebuffer(read_target,(unsigned)framebuffer);
    static int captured_detail;
    int has_detail=0;
    for (int i=4;i<800*480*4;i+=4) {
        if (pixels[i]!=pixels[0] || pixels[i+1]!=pixels[1] || pixels[i+2]!=pixels[2]) {
            has_detail=1;
            break;
        }
    }
    if (captured_detail && !has_detail) {
        free(pixels);
        return;
    }
    FILE *file=fopen(temporary,"wb");
    if (file) {
        int ok=fprintf(file,"P6\n800 480\n255\n")>0;
        unsigned char row[800*3];
        for (int y=479;y>=0 && ok;y--) {
            for(int x=0;x<800;x++) {
                unsigned char *pixel=pixels+(y*800+x)*4;
                row[x*3]=pixel[0];row[x*3+1]=pixel[1];row[x*3+2]=pixel[2];
            }
            ok=fwrite(row,1,sizeof(row),file)==sizeof(row);
        }
        if (fclose(file)!=0) ok=0;
        if (ok && rename(temporary,path)==0) {
            captured_detail=has_detail;
            fprintf(stderr,"NAC_EGL_SWAP_CAPTURE_OK\n");
        }
        else unlink(temporary);
    }
    free(pixels);
}

unsigned eglSwapBuffers(void *display, void *surface) {
    unsigned (*swap)(void *,void *)=dlsym(NEXT,"eglSwapBuffers");
    const char *path=getenv("NAC_EGL_CAPTURE");
    static unsigned swaps;
    static int capture_busy;
    if (path && *path) {
        unsigned count=__sync_add_and_fetch(&swaps,1);
        if ((count<=6 || count%30==0) && !__sync_lock_test_and_set(&capture_busy,1)) {
            capture_surface(display,surface,path);
            __sync_lock_release(&capture_busy);
        }
    }
    return swap ? swap(display,surface) : 0;
}
