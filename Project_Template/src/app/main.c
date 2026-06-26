#include "stm32f10x.h" 
#include "stm32f10x_gpio.h" 
#include "stm32f10x_rcc.h"
#include "Delay.h"

int main(void)
{
    // 开启 RCC 时钟总线 
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);

    //定义 gpio 结构体 
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz; 
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    // 默认关闭  低电平灭，高电平亮 
    GPIO_SetBits(GPIOC, GPIO_Pin_13);
    

    while (1) 
    {
        // 灯灭
        GPIO_SetBits(GPIOC, GPIO_Pin_13);
        Delay_ms(500);
        // 灯亮
        GPIO_ResetBits(GPIOC, GPIO_Pin_13);
        Delay_ms(500);
    }
}
