# ==============================================================================
# 模块名称: cmsis (Cortex Microcontroller Software Interface Standard)
# 模块职责: 提供 ARM 内核标准接口、系统初始化代码及底层寄存器定义
# ==============================================================================

# 1. 声明目标：创建一个名为 cmsis 的静态库（不直接在此处绑定源文件，保持灵活性）
add_library(cmsis STATIC) 

# 2. 填充源文件：将系统初始化代码作为 PRIVATE（私有）实现添加
#    上层模块不需要知道 system_stm32f10x.c 的存在，只需调用其暴露的 SystemInit()
target_sources(cmsis PRIVATE 
    system_stm32f10x.c 
)

# 3. 公开头文件路径：使用生成器表达式，实现构建与安装路径的完美解耦
target_include_directories(cmsis PUBLIC 
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}> 
    $<INSTALL_INTERFACE:include> 
)

# 4. 传递依赖：公开链接芯片配置模块 (stm32_config)
#    利用 PUBLIC 特性，将 -DSTM32F10X_MD 等全局宏定义自动“传染”给所有依赖 cmsis 的上层模块
target_link_libraries(cmsis PUBLIC 
    stm32_config 
)
