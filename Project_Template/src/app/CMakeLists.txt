# ==============================================================================
# 模块名称: app (纯业务逻辑层)
# 模块职责: 封装 main 及业务算法，供壳工程链接
# ==============================================================================

add_library(app STATIC)

# 仅保留纯业务代码，中断文件已移至根目录壳工程
target_sources(app PRIVATE
    main.c
)

target_include_directories(app PRIVATE .)

target_link_libraries(app PRIVATE 
    bsp 
    common 
    driver
)
