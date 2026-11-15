#ifndef NAC_RUNTIME_H
#define NAC_RUNTIME_H
/* Minimal public C ABI declarations for helpers linked to firmware libc. */
typedef struct _IO_FILE FILE;
extern FILE *stdout, *stderr;
extern void setbuf(FILE *, char *);
extern int puts(const char *);
extern int printf(const char *, ...);
extern int fprintf(FILE *, const char *, ...);
extern FILE *fopen(const char *, const char *);
extern __SIZE_TYPE__ fwrite(const void *, __SIZE_TYPE__, __SIZE_TYPE__, FILE *);
extern int fclose(FILE *);
extern void *calloc(__SIZE_TYPE__, __SIZE_TYPE__);
extern void free(void *);
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern char *dlerror(void);
#define NULL ((void *)0)
#define RTLD_NOW 2
#define RTLD_GLOBAL 0x100
int main(int, char **);
extern void __libc_start_main(int (*)(int, char **), int, char **,
                              void *, void *, void *, void *) __attribute__((noreturn));
__attribute__((used, noreturn)) void nac_start(long *stack) {
    __libc_start_main(main, (int)stack[0], (char **)(stack+1), NULL, NULL, NULL, stack);
}
__attribute__((naked, noreturn)) void _start(void) {
    __asm__ volatile("mov r0, sp\n" "b nac_start\n");
}
#endif
