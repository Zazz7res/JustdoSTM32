# ==============================================================================
# 模块名称: app (应用业务逻辑层)
# 模块职责: 封装纯业务逻辑，编译为静态库，供最终的固件壳工程链接
# ==============================================================================

# 1. 声明为静态库（业务逻辑与底层硬件启动解耦）
add_library(app STATIC)

# 2. 添加私有源文件
target_sources(app PRIVATE
    main.c
)

# 3. 头文件路径（如果 app 内部文件不需要互相 include，这行可直接删除）
# 使用 '.' 代替冗长的内置变量；如果不需要对外暴露，改用 PRIVATE
target_include_directories(app PRIVATE .)

# 4. 私有链接底层模块（完美利用依赖传递，无需重复链接 cmsis）
target_link_libraries(app PRIVATE 
    bsp 
    common 
    driver
)
