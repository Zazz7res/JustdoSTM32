


# ------------------------------------------------------------------------------
# ARM GCC Toolchain File for STM32F103 (Cortex-M3)
# ------------------------------------------------------------------------------
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR cortex-m3)

# 优先使用环境变量 ARM_TOOLCHAIN_PATH，否则使用默认路径
if(DEFINED ENV{ARM_TOOLCHAIN_PATH})
    set(TOOLCHAIN_PATH "$ENV{ARM_TOOLCHAIN_PATH}")
else()
    set(TOOLCHAIN_PATH "/opt/arm-gcc/arm-gnu-toolchain-15.2.rel1-x86_64-arm-none-eabi/bin")
endif()

message(STATUS "Toolchain path: ${TOOLCHAIN_PATH}")

# 指定编译器
set(CMAKE_C_COMPILER      ${TOOLCHAIN_PATH}/arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER    ${TOOLCHAIN_PATH}/arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER    ${TOOLCHAIN_PATH}/arm-none-eabi-gcc)
set(CMAKE_OBJCOPY         ${TOOLCHAIN_PATH}/arm-none-eabi-objcopy)
set(CMAKE_SIZE_UTIL       ${TOOLCHAIN_PATH}/arm-none-eabi-size)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# 基本编译选项
set(COMMON_FLAGS "-mcpu=cortex-m3 -mthumb -mfloat-abi=soft")
set(CMAKE_C_FLAGS   "${COMMON_FLAGS} -std=gnu11" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS "${COMMON_FLAGS} -std=gnu++14" CACHE STRING "" FORCE)
set(CMAKE_ASM_FLAGS "${COMMON_FLAGS} -x assembler-with-cpp" CACHE STRING "" FORCE)

# 链接器初始标志（同样使用 nano，并开启 gc-sections）
set(CMAKE_EXE_LINKER_FLAGS "-Wl,--gc-sections" CACHE STRING "" FORCE)

# 搜索规则
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
