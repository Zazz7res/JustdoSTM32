# ==============================================================================# ==============================================================================
# 模块名称: common (项目级公共工具库)
# 模块职责: 提供系统调用重定向等底层胶水代码
# ==============================================================================

add_library(common STATIC)

# 根据实际文件树，目前仅有 syscalls.c (后续可加 Delay.c, Timer.c 等)
target_sources(common PRIVATE
    syscalls.c
    Delay.c
)

target_include_directories(common PUBLIC .)

# syscalls.c 内部通常需要调用 driver 层的串口发送函数
target_link_libraries(common PRIVATE 
    driver 
    cmsis
)
