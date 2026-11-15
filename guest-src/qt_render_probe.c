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
