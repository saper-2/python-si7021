# python-si7021
Si7021 python interface class for easier usage

I've got some of those sensors from ali so I had to test them, because I had Rpi at hand so I commited a simple driver :)
I have got GY-21 si7021 modules for about 2USD/1pcs .

In img dir u'll find few photos of module.

# Wiring
Nothing dificult.
```
Si7021 -- Pi
VIN    -- 3V3 (J8 pin 1)
GND    -- GND (J8 pin 6)
SCL    -- SCL (J8 pin 5)
SDA    -- SDA (J8 pin 3)
```

# Heater of Si7021
If you read datasheet of Si7021 and paid more attention to Heater control register then u might notice that this is not really much linear at first glance.
It took me a a bit of time to find out a reasonable coefficeint for calculating more-or-less precise current.  

Screenshot of my excel :) :
[img/si7021-heater-current-coeff-calcs.png]

And the graph:
[img/si7021-heater-current-graph.png]

# Files
## si7021.py
Main file with class Si7021

## si7021_test.py
Test code for Si7021 class and example how to use it :)

## si7021_test_no_class.py
No class version of Si7021 routines - this was my first test zone :)

# EOF
I might never update it anymore :) becasue it have all functionality that I need, if you manage to add some extra functionality then feel free to request merge. Or I can add your code manually and push updates to repo.
