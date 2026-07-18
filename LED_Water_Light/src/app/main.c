#include "stm32f10x.h" 
#include "stm32f10x_gpio.h" 
#include "stm32f10x_rcc.h"
#include "Delay.h"

int main(void) 
{
    // 开启 RCC GPIOA 时钟 
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);
    
    // 声明 GPIO 配置结构体
    GPIO_InitTypeDef GPIO_InitStructure;
    
    // 设置工作模式 
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    // 选择操作引脚
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_All;
    // 设置引脚翻转速度
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    // 将结构体配置写入 GPIOA 寄存器
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    while (1) 
    {
        GPIO_Write(GPIOA, ~0x0001);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0002);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0004);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0008);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0010);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0020);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0040);
        Delay_ms(500);

        GPIO_Write(GPIOA, ~0x0080);
        Delay_ms(500);
    }
}

    

