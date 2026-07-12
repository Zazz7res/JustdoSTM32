/*=============================================================================
  Linker script for STM32F103C8T6 (64KB Flash, 20KB RAM)
  Designed for: arm-none-eabi-gcc (GNU LD)
  Project path: src/startup/STM32F103C8T6_FLASH.ld
=============================================================================*/

/* 指定输出格式为 32 位小端 ARM 的 ELF 文件 */
OUTPUT_FORMAT("elf32-littlearm", "elf32-bigarm", "elf32-littlearm")
OUTPUT_ARCH(arm)

/* 程序入口点，由启动文件中的 Reset_Handler 定义 */
ENTRY(Reset_Handler)

/*=============================================================================
  内存区域定义 (Memory Map)
  STM32F103C8T6 的实际物理内存布局：
  - Flash: 起始地址 0x08000000，容量 64KB (0x10000 字节)
  - SRAM:  起始地址 0x20000000，容量 20KB (0x5000 字节)
=============================================================================*/
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K  /* 代码和常量 */
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 20K  /* 变量和堆栈 */
}

/*=============================================================================
  栈和堆的大小定义
  - _Min_Stack_Size: 最小栈大小，用于函数调用和局部变量
  - _Min_Heap_Size:  最小堆大小，用于动态内存分配 (malloc/free)
=============================================================================*/
_Min_Stack_Size = 0x400;   /* 1KB 栈空间 */
_Min_Heap_Size  = 0x200;   /* 512B 堆空间，若不使用 malloc，可设为 0 */

/*=============================================================================
  各输出段的布局 (Sections Layout)
=============================================================================*/
SECTIONS
{
    /* 1. 中断向量表 (Vector Table) —— 必须放在 Flash 最开头
       CPU 上电后首先从 0x08000000 读取 SP，再从 0x08000004 读取 Reset_Handler 地址 */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))   /* 保留向量表，防止被优化移除 */
        . = ALIGN(4);
    } > FLASH

    /* 2. 代码段 (Code Section) —— 存放程序指令 */
    .text :
    {
        . = ALIGN(4);
        *(.text)               /* 所有 .text 段 */
        *(.text*)              /* 所有 .text.* 段，如 .text.foo */
        *(.glue_7)             /* ARM/Thumb 代码胶合 */
        *(.glue_7t)
        *(.eh_frame)           /* 异常处理框架信息 */

        KEEP (*(.init))        /* 构造函数 */
        KEEP (*(.fini))        /* 析构函数 */

        . = ALIGN(4);
        _etext = .;            /* 代码段结束地址 */
    } > FLASH

    /* 3. 只读数据段 (Read-Only Data) —— 存放常量、字符串等 */
    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)             /* 所有 .rodata 段 */
        *(.rodata*)            /* 所有 .rodata.* 段 */
        . = ALIGN(4);
    } > FLASH

    /* ARM 异常处理相关 */
    .ARM.extab   : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > FLASH
    .ARM : {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } > FLASH

    /* 预初始化数组 (用于 C++ 全局对象构造) */
    .preinit_array :
    {
        PROVIDE_HIDDEN (__preinit_array_start = .);
        KEEP (*(.preinit_array*))
        PROVIDE_HIDDEN (__preinit_array_end = .);
    } > FLASH
    .init_array :
    {
        PROVIDE_HIDDEN (__init_array_start = .);
        KEEP (*(SORT(.init_array.*)))
        KEEP (*(.init_array*))
        PROVIDE_HIDDEN (__init_array_end = .);
    } > FLASH
    .fini_array :
    {
        PROVIDE_HIDDEN (__fini_array_start = .);
        KEEP (*(SORT(.fini_array.*)))
        KEEP (*(.fini_array*))
        PROVIDE_HIDDEN (__fini_array_end = .);
    } > FLASH

    /*=========================================================================
       4. 数据段 (Data Section) —— 已初始化的全局变量
       - 加载地址 (LMA) 在 Flash，链接地址 (VMA) 在 RAM
       - 启动代码负责将数据从 Flash 复制到 RAM
    =========================================================================*/
    _sidata = LOADADDR(.data);   /* Flash 中 .data 段的起始地址 */

    .data :
    {
        . = ALIGN(4);
        _sdata = .;              /* RAM 中 .data 段的起始地址 */
        *(.data)                 /* 所有 .data 段 */
        *(.data*)                /* 所有 .data.* 段 */

        . = ALIGN(4);
        _edata = .;              /* RAM 中 .data 段的结束地址 */
    } > RAM AT> FLASH

    /*=========================================================================
       5. BSS 段 (Block Started by Symbol) —— 未初始化的全局变量
       - 启动代码负责将这段 RAM 清零
    =========================================================================*/
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;               /* BSS 段起始地址 */
        __bss_start__ = _sbss;
        *(.bss)
        *(.bss*)
        *(COMMON)                /* 未放到特定段的公共符号 */

        . = ALIGN(4);
        _ebss = .;               /* BSS 段结束地址 */
        __bss_end__ = _ebss;
    } > RAM

    /*=========================================================================
       6. 堆 (Heap) 和栈 (Stack) 定义
       - 栈从 RAM 最高地址向下增长
       - 堆从 BSS 段结束后向上增长
    =========================================================================*/
    ._user_heap_stack :
    {
        . = ALIGN(4);
        PROVIDE ( end = . );
        PROVIDE ( _end = . );
        . = . + _Min_Heap_Size;
        . = . + _Min_Stack_Size;
        . = ALIGN(4);
    } > RAM

    /DISCARD/ : {
    *(.comment)
    *(.note*)
    *(.debug_*)
}

    /* 定义栈顶地址 —— 指向 RAM 的末尾 */
    _estack = ORIGIN(RAM) + LENGTH(RAM);
}
