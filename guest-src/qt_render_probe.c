#include "runtime.h"

/* Exact Qt 5.5 ARM ABI probe, using the firmware's own Qt paint engine.
 * Oversized zeroed buffers hold Qt objects; their private state is owned by Qt.
 * QWindow's QSurface base is at +8 on this firmware (QWindow destructor thunk).
 * This diagnostic scene is deliberately unrelated to the Peugeot HMI. */
int main(int argc, char **argv) {
    setbuf(stdout, NULL);
    void *gui = dlopen("libQt5Gui.so.5", RTLD_NOW | RTLD_GLOBAL);
    if (!gui) { fprintf(stderr,"Qt load: %s\n",dlerror()); return 1; }
#define QT(ret,name,symbol,args) ret (*name) args = dlsym(gui,symbol); \
    if (!name) { fprintf(stderr,"Qt ABI missing: %s\n",symbol); return 2; }
    QT(void, app_ctor, "_ZN15QGuiApplicationC1ERiPPci", (void *,int *,char **,int));
    QT(void, app_dtor, "_ZN15QGuiApplicationD1Ev", (void *));
    QT(void, window_ctor, "_ZN7QWindowC1EP7QScreen", (void *,void *));
    QT(void, window_dtor, "_ZN7QWindowD2Ev", (void *));
    QT(void, surface_type, "_ZN7QWindow14setSurfaceTypeEN8QSurface11SurfaceTypeE", (void *,int));
    QT(void, resize, "_ZN7QWindow6resizeEii", (void *,int,int));
    QT(void, window_create, "_ZN7QWindow6createEv", (void *));
    QT(void, context_ctor, "_ZN14QOpenGLContextC1EP7QObject", (void *,void *));
    QT(void, context_dtor, "_ZN14QOpenGLContextD1Ev", (void *));
    QT(unsigned char, context_create, "_ZN14QOpenGLContext6createEv", (void *));
    QT(unsigned char, make_current, "_ZN14QOpenGLContext11makeCurrentEP8QSurface", (void *,void *));
    QT(void, done_current, "_ZN14QOpenGLContext11doneCurrentEv", (void *));
    QT(void, swap_buffers, "_ZN14QOpenGLContext11swapBuffersEP8QSurface", (void *,void *));
    QT(void, device_ctor, "_ZN18QOpenGLPaintDeviceC1Eii", (void *,int,int));
    QT(void, device_dtor, "_ZN18QOpenGLPaintDeviceD1Ev", (void *));
    QT(void, painter_ctor, "_ZN8QPainterC1EP12QPaintDevice", (void *,void *));
    QT(void, painter_dtor, "_ZN8QPainterD2Ev", (void *));
    QT(void, color_ctor, "_ZN6QColorC1EN2Qt11GlobalColorE", (void *,int));
    QT(void, fill_rect, "_ZN8QPainter8fillRectERK5QRectRK6QColor", (void *,const int *,void *));
    void *app=calloc(1,65536), *window=calloc(1,65536), *context=calloc(1,65536);
    void *device=calloc(1,65536), *painter=calloc(1,65536);
    if (!app || !window || !context || !device || !painter) return 3;
    app_ctor(app,&argc,argv,0x050500);
    window_ctor(window,NULL);
    surface_type(window,1); /* OpenGLSurface */
    resize(window,800,480);
    window_create(window);
    context_ctor(context,NULL);
    if (!context_create(context) || !make_current(context,(char *)window+8)) {
        fprintf(stderr,"Qt could not make a real GL context current\n"); return 4;
    }
    puts("NAC_QT_GL_CONTEXT_CURRENT");
    void *gles=dlopen("libGLESv2.so.2",RTLD_NOW|RTLD_GLOBAL);
    if (!gles) return 5;
    void (*read_pixels)(int,int,int,int,unsigned,unsigned,void *)=dlsym(gles,"glReadPixels");
    unsigned (*get_error)(void)=dlsym(gles,"glGetError");
    const unsigned char *(*get_string)(unsigned)=dlsym(gles,"glGetString");
    if (!read_pixels || !get_error || !get_string) return 5;
    printf("QT_GL_RENDERER=%s\n",get_string(0x1f01));
    device_ctor(device,800,480);
    painter_ctor(painter,device);
    const int rectangles[][4]={{0,0,799,479},{40,40,759,119},{40,160,379,439},{420,160,759,439}};
    const int colors[]={15,10,7,8};
    for (int i=0;i<4;i++) {
        unsigned color[16]={0};
        color_ctor(color,colors[i]);
        fill_rect(painter,rectangles[i],color);
    }
    painter_dtor(painter); /* Ends painting and submits the Qt GL paint engine work. */
    unsigned char *pixels=calloc(800*480,4);
    if (!pixels) return 6;
    read_pixels(0,0,800,480,0x1908,0x1401,pixels);
    unsigned error=get_error();
    unsigned char *background=pixels+((480-1-10)*800+10)*4;
    unsigned char *bar=pixels+((480-1-80)*800+400)*4;
    unsigned char *red=pixels+((480-1-300)*800+200)*4;
    unsigned char *green=pixels+((480-1-300)*800+600)*4;
    printf("QT_GL_ERROR=0x%x QT_RED=%u,%u,%u QT_GREEN=%u,%u,%u\n",error,
           red[0],red[1],red[2],green[0],green[1],green[2]);
    if (error || background[0] || background[1] || background[2]!=128 ||
        bar[0] || bar[1]!=255 || bar[2]!=255 ||
        red[0]!=255 || red[1] || red[2] || green[0] || green[1]!=255 || green[2]) return 7;
    FILE *frame=fopen("/tmp/nac-qt-render.ppm","wb");
    if (!frame) return 8;
    fprintf(frame,"P6\n800 480\n255\n");
    for(int y=479;y>=0;y--) for(int x=0;x<800;x++) fwrite(pixels+(y*800+x)*4,1,3,frame);
    fclose(frame);
    /* Put non-default GL readback state in place. The presentation capture
     * must read the window, preserve this state, and match the direct image. */
    void (*get_integer)(unsigned,int *)=dlsym(gles,"glGetIntegerv");
    void (*pixel_store)(unsigned,int)=dlsym(gles,"glPixelStorei");
    void (*gen_framebuffers)(int,unsigned *)=dlsym(gles,"glGenFramebuffers");
    void (*bind_framebuffer)(unsigned,unsigned)=dlsym(gles,"glBindFramebuffer");
    void (*delete_framebuffers)(int,const unsigned *)=dlsym(gles,"glDeleteFramebuffers");
    void (*gen_buffers)(int,unsigned *)=dlsym(gles,"glGenBuffers");
    void (*bind_buffer)(unsigned,unsigned)=dlsym(gles,"glBindBuffer");
    void (*buffer_data)(unsigned,__PTRDIFF_TYPE__,const void *,unsigned)=dlsym(gles,"glBufferData");
    void (*delete_buffers)(int,const unsigned *)=dlsym(gles,"glDeleteBuffers");
    if (!get_integer || !pixel_store || !gen_framebuffers || !bind_framebuffer ||
        !delete_framebuffers || !gen_buffers || !bind_buffer || !buffer_data || !delete_buffers) return 9;
    const unsigned char *version=get_string(0x1f02);
    int es3=version && version[10]>='3' && version[10]<='9';
    unsigned read_target=es3 ? 0x8ca8 : 0x8d40;
    unsigned read_fbo=0,pack_buffer=0;
    gen_framebuffers(1,&read_fbo);
    bind_framebuffer(read_target,read_fbo);
    pixel_store(0x0d05,8);
    if (es3) {
        gen_buffers(1,&pack_buffer);
        bind_buffer(0x88eb,pack_buffer);
        buffer_data(0x88eb,2*1024*1024,NULL,0x88e1);
        pixel_store(0x0d02,803);pixel_store(0x0d03,1);pixel_store(0x0d04,1);
    }
    swap_buffers(context,(char *)window+8);
    int actual=0;
    get_integer(es3 ? 0x8caa : 0x8ca6,&actual);
    if ((unsigned)actual!=read_fbo) return 10;
    get_integer(0x0d05,&actual);
    if (actual!=8) return 10;
    if (es3) {
        get_integer(0x88ed,&actual);if((unsigned)actual!=pack_buffer) return 10;
        get_integer(0x0d02,&actual);if(actual!=803) return 10;
        get_integer(0x0d03,&actual);if(actual!=1) return 10;
        get_integer(0x0d04,&actual);if(actual!=1) return 10;
        bind_buffer(0x88eb,0);delete_buffers(1,&pack_buffer);
        pixel_store(0x0d02,0);pixel_store(0x0d03,0);pixel_store(0x0d04,0);
    }
    pixel_store(0x0d05,4);
    bind_framebuffer(read_target,0);delete_framebuffers(1,&read_fbo);
    if (get_error()) return 10;
    puts("NAC_EGL_CAPTURE_STATE_OK");
    free(pixels);
    device_dtor(device);
    done_current(context);
    context_dtor(context);
    window_dtor(window);
    app_dtor(app);
    free(painter);free(device);free(context);free(window);free(app);
    puts("NAC_QT_SOFTWARE_PAINT_OK");
    return 0;
}
