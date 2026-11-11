## 1. LED_Blink

<img alt="LED_Blinks_001" src="./img_led/led_01.png" style="zoom: 80%;" />
<br>

<img alt="007" src="./img_led/led_02.png" style="zoom: 80%;" />
<br>

<img alt="008" src="./img_led/led_03.png" style="zoom: 80%;" />
<br>

<img alt="LED_Blinks_006" src="./img_led/led_04.png" style="zoom: 80%;" />
<br>

<img alt="009" src="./img_led/led_05.png" style="zoom: 80%;" />
<br>

<img alt="010" src="./img_led/led_06.png" style="zoom: 80%;" />
<br>

* main.c
```c
  /* USER CODE BEGIN WHILE */
  while (1)
  {
	  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, 1);
	  HAL_Delay(1000);
	  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, 0);
	  HAL_Delay(1000);

    // HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
    // HAL_Delay(1000);
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
```

