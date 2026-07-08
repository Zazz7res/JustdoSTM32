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

