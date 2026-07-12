#include "stm32f10x.h"          // STM32F10x 标准库外设库总头文件 
#include "stm32f10x_gpio.h"     // GPIO 外设函数与类型声明  
#include "stm32f10x_rcc.h"      // RCC 时钟控制函数声明  
#include "Delay.h"              // 自制延时函数库  

int main(void) 
{
    // 开启  RCC 时钟 
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    // 定义 GPIO 结构体 
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // 高电平灯灭，低电平灯亮  
    // 默认高电平
    GPIO_SetBits(GPIOA, GPIO_Pin_6);

    while(1)
    {
        GPIO_ResetBits(GPIOA, GPIO_Pin_6);
        Delay_ms(500);
        GPIO_SetBits(GPIOA, GPIO_Pin_6);
        Delay_ms(500);
    }
}
