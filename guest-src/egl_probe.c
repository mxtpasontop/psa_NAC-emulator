#include "runtime.h"

/* Real EGL/GLES2 pbuffer test. No device handles or rendered pixels are faked. */
int main(int argc, char **argv) {
    (void)argc; (void)argv;
    setbuf(stdout, NULL);
    void *egl = dlopen("libEGL.so.1", RTLD_NOW | RTLD_GLOBAL);
    if (!egl) { fprintf(stderr, "EGL load: %s\n", dlerror()); return 1; }
    void *gles = dlopen("libGLESv2.so.2", RTLD_NOW | RTLD_GLOBAL);
    if (!gles) { fprintf(stderr, "GLES load: %s\n", dlerror()); return 1; }
#define EGL(ret, name, args) ret (*name) args = (void *)dlsym(egl, #name); if (!name) return 2
#define GL(ret, name, args) ret (*name) args = (void *)dlsym(gles, #name); if (!name) return 2
    EGL(void *, eglGetDisplay, (void *));
    EGL(unsigned, eglInitialize, (void *, int *, int *));
    EGL(unsigned, eglBindAPI, (unsigned));
    EGL(unsigned, eglChooseConfig, (void *, const int *, void **, int, int *));
    EGL(void *, eglCreatePbufferSurface, (void *, void *, const int *));
    EGL(void *, eglCreateContext, (void *, void *, void *, const int *));
    EGL(unsigned, eglMakeCurrent, (void *, void *, void *, void *));
    EGL(int, eglGetError, (void));
    GL(const unsigned char *, glGetString, (unsigned));
    GL(void, glClearColor, (float, float, float, float));
    GL(void, glClear, (unsigned));
    GL(void, glReadPixels, (int, int, int, int, unsigned, unsigned, void *));
    GL(unsigned, glGetError, (void));
    void *display = eglGetDisplay(NULL);
    int major=0, minor=0;
    if (!display || !eglInitialize(display, &major, &minor)) {
        fprintf(stderr, "eglInitialize failed: 0x%x\n", eglGetError()); return 3;
    }
    printf("EGL_INITIALIZED=%d.%d\n", major, minor);
    eglBindAPI(0x30a0); /* EGL_OPENGL_ES_API */
    int attributes[] = {0x3033,1,0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038};
    void *config=NULL;
    int count=0;
    if (!eglChooseConfig(display,attributes,&config,1,&count) || !count) {
        fprintf(stderr,"No pbuffer ES2 config: 0x%x\n",eglGetError()); return 4;
    }
    int size[]={0x3057,16,0x3056,16,0x3038};
    int version[]={0x3098,2,0x3038};
    void *surface=eglCreatePbufferSurface(display,config,size);
    void *context=eglCreateContext(display,config,NULL,version);
    if (!surface || !context || !eglMakeCurrent(display,surface,surface,context)) {
        fprintf(stderr,"EGL context failed: 0x%x\n",eglGetError());return 5;
    }
    printf("GL_RENDERER=%s\nGL_VERSION=%s\n",glGetString(0x1f01),glGetString(0x1f02));
    glClearColor(0.125f,0.5f,0.875f,1.0f);
    glClear(0x4000);
    unsigned char pixels[16*16*4];
    glReadPixels(0,0,16,16,0x1908,0x1401,pixels);
    unsigned error=glGetError();
    printf("GL_PIXEL=%u,%u,%u,%u ERROR=0x%x\n",pixels[0],pixels[1],pixels[2],pixels[3],error);
    if (error || pixels[0]<31 || pixels[0]>33 || pixels[1]<127 || pixels[1]>129 ||
        pixels[2]<222 || pixels[2]>224 || pixels[3]!=255) return 6;
    FILE *frame=fopen("/tmp/nac-render.ppm","wb");
    if (!frame) return 7;
    fprintf(frame,"P6\n16 16\n255\n");
    for (int y=15;y>=0;y--) for(int x=0;x<16;x++) fwrite(pixels+(y*16+x)*4,1,3,frame);
    fclose(frame);
    puts("NAC_SOFTWARE_GLES_OK");
    return 0;
}
