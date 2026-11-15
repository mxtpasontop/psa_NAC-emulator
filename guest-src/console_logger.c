typedef struct _IO_FILE FILE;
extern FILE *stderr;
extern int fputs(const char *, FILE *);
extern int fprintf(FILE *, const char *, ...);
extern int snprintf(char *, __SIZE_TYPE__, const char *, ...);

/* Diagnostic implementation of libOvipLogger's backend ABI, established from
 * the local library's dlsym calls. Only the VM's backend-directory bind mount
 * uses this library; no OEM library or executable is patched. */
static char application[32] = "NAC";
void init(void) { fputs("NAC_CONSOLE_LOGGER_READY\n", stderr); }
void cleanup(void) { }
void registerApplication(const char *name, const char *description) {
    snprintf(application, sizeof(application), "%s", name ? name : "NAC");
    fprintf(stderr, "[%s] %s\n", application, description ? description : "");
}
void registerContext(const char *name, const char *description) {
    (void)name; (void)description;
}
void print(const char *context, int level, const char *message) {
    fprintf(stderr, "[%s/%s:%d] %s\n", application, context ? context : "", level,
            message ? message : "");
}
