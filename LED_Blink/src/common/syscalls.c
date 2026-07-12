/*
* syscalls.c
* 裸机 newlib-nano 系统调用实现（工业级模板）
*/

#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>

/* -------------- 输出通道配置 ---------------- */
// 若使用 J-Link/ST-Link + SWO 调试输出，请取消下面宏的注释
// #define USE_ITM_PRINTF

#ifdef USE_ITM_PRINTF
  #define ITM_Port8(n)    (*(volatile uint8_t *)(0xE0000000 + 4*(n)))
  #define ITM_Port32(n)   (*(volatile uint32_t*)(0xE0000000 + 4*(n)))
  static int itm_send_char(int ch) {
      if ((ITM_Port32(0) & 1) == 0) return -1;
      ITM_Port8(0) = (uint8_t)ch;
      return ch;
  }
#else
  #include "stm32f10x_usart.h"
  static int usart_send_char(int ch) {
      uint32_t timeout = 10000U;
      while (USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET) {
          if (--timeout == 0U) return -1;  /* USART 未初始化或异常，直接放弃 */
      }
      USART_SendData(USART1, (uint8_t)ch);
      return ch;
  }
#endif

/* ------------ printf 输出重定向 --------------- */
int _write(int fd, char *ptr, int len) {
  (void)fd;
  for (int i = 0; i < len; i++) {
#ifdef USE_ITM_PRINTF
      itm_send_char(ptr[i]);
#else
      usart_send_char(ptr[i]);
#endif
  }
  return len;
}

/* ------------ 堆管理（malloc 需要） ----------- */
extern char _end;   /* 链接脚本定义 */
static char *heap_end = 0;

void *_sbrk(int incr) {
  char *prev_heap_end;
  if (heap_end == 0) heap_end = &_end;
  prev_heap_end = heap_end;

  uint32_t sp;
  __asm volatile ("mov %0, sp" : "=r"(sp));
  if (heap_end + incr > (char *)sp) {
      errno = ENOMEM;
      return (void *)-1;
  }
  heap_end += incr;
  return (void *)prev_heap_end;
}

/* ---------- 其余必要桩函数 -------------------- */
int _close(int fd) {
  (void)fd;
  errno = EBADF;
  return -1;
}

int _fstat(int fd, struct stat *st) {
  (void)fd;
  st->st_mode = S_IFCHR;
  return 0;
}

int _isatty(int fd) {
  (void)fd;
  return 1;
}

off_t _lseek(int fd, off_t ptr, int dir) {
  (void)fd; (void)ptr; (void)dir;
  errno = EBADF;
  return -1;
}

int _read(int fd, char *ptr, int len) {
  (void)fd; (void)ptr; (void)len;
  errno = EBADF;
  return -1;
}

void _exit(int status) {
  (void)status;
  while (1);   // 死循环，等待看门狗复位
}

int _kill(pid_t pid, int sig) {
  (void)pid; (void)sig;
  errno = EINVAL;
  return -1;
}

pid_t _getpid(void) {
  return 1;
}
