"""Build/test the exported C routine with a local fake FATFS, never with keys."""
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_sgm import EXPORT_FUNCTION

NATIVE_PREFIX = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdarg.h>
#include <unistd.h>
#define FR_OK 0
#define FR_EXIST 1
#define FR_FAIL 2
#define SZ_32K 32768
#define EPRINTF(msg) fprintf(stderr,"%s\\n", msg)
typedef unsigned int u32;
typedef int FRESULT;
typedef struct { unsigned long fsize; } FILINFO;
static char prefix[1024];
static int fail_new_rename = 0;
static const char *map(const char *path) {
    static char buf[4][2048];
    static int next = 0;
    char *v=buf[(next++) % 4];
    if (strncmp(path, "sd:/", 4) != 0) abort();
    snprintf(v, 2048, "%s/%s", prefix, path+4);
    return v;
}
static FRESULT f_mkdir(const char *p) {
    const char *s=map(p);
    if (mkdir(s, 0700)==0) return FR_OK;
    return errno==EEXIST?FR_EXIST:FR_FAIL;
}
static FRESULT f_stat(const char *p, FILINFO *f) {
    struct stat s;
    if (stat(map(p), &s)) return FR_FAIL;
    if(f) f->fsize=(unsigned long)s.st_size;
    return FR_OK;
}
static FRESULT f_unlink(const char *p) { return unlink(map(p))==0?FR_OK:FR_FAIL; }
static FRESULT f_rename(const char *src, const char *dst) {
    if (fail_new_rename && strstr(src,"keys.sgm.tmp") && strstr(dst,"keys.txt")) return FR_FAIL;
    return rename(map(src),map(dst))==0?FR_OK:FR_FAIL;
}
static int sd_save_to_file(const void *data, u32 len, const char *p) {
    FILE *f=fopen(map(p),"wb");
    if(!f) return 1;
    size_t n=fwrite(data,1,len,f);
    int result=fclose(f);
    return n==len && result==0?0:1;
}
static int gfx_printf(const char *fmt, ...) {
    va_list args;
    va_start(args,fmt);
    int n=vprintf(fmt,args);
    va_end(args);
    return n;
}
'''
NATIVE_MAIN = r'''
static void load(char *p,size_t n,const char *path) {
   FILE *f=fopen(map(path),"rb");
   if(!f)abort();
   size_t r=fread(p,1,n,f);
   if (r!=n)abort();
   fclose(f);
}
int main(int argc, char **argv) {
  if(argc!=2)return 2;
  snprintf(prefix,sizeof(prefix),"%s",argv[1]);
  char d[1500],newd[1500],otherd[1500],readbuf[1500];
  memset(d,'1',sizeof(d)); memset(newd,'2',sizeof(newd)); memset(otherd,'3',sizeof(otherd));
  memcpy(d,"master_key_",11); memcpy(newd,"master_key_",11); memcpy(otherd,"master_key_",11);
  d[sizeof(d)-1]=0; newd[sizeof(newd)-1]=0; otherd[sizeof(otherd)-1]=0;
  if(f_mkdir("sd:/switch")!=FR_OK)return 3;
  _sgm_export_tinfoil_keys(d);
  memset(readbuf,0,sizeof(readbuf));load(readbuf,strlen(d),"sd:/switch/tinfoil/keys.txt");
  if(memcmp(readbuf,d,strlen(d)))return 4;
  _sgm_export_tinfoil_keys(newd);
  memset(readbuf,0,sizeof(readbuf));load(readbuf,strlen(d),"sd:/switch/tinfoil/keys.sgm.bak");
  if(memcmp(readbuf,d,strlen(d)))return 5;
  memset(readbuf,0,sizeof(readbuf));load(readbuf,strlen(newd),"sd:/switch/tinfoil/keys.txt");
  if(memcmp(readbuf,newd,strlen(newd)))return 6;
  fail_new_rename=1;
  _sgm_export_tinfoil_keys(otherd);
  memset(readbuf,0,sizeof(readbuf));load(readbuf,strlen(newd),"sd:/switch/tinfoil/keys.txt");
  if(memcmp(readbuf,newd,strlen(newd)))return 7;
  puts("SGM_NATIVE_EXPORT_TEST_PASS");
  return 0;
}
'''
class NativeExporterTest(unittest.TestCase):
    def test_copy_backup_and_rollback(self):
        gcc=shutil.which('gcc')
        if not gcc:
            self.skipTest('gcc not installed; GitHub Actions installs it')
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'test.c'
            exe=Path(temp)/'test'
            root=Path(temp)/'sd'
            root.mkdir()
            source.write_text(NATIVE_PREFIX+EXPORT_FUNCTION+NATIVE_MAIN)
            cp=subprocess.run([gcc,'-std=gnu11','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0, cp.stderr)
            run=subprocess.run([str(exe),str(root)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr+'\n'+run.stdout)
            self.assertIn('SGM_NATIVE_EXPORT_TEST_PASS',run.stdout)
