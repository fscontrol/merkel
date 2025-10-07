from merkel import CoolingTower, WaterFlow, AirFlow
#расчет градирни
hot_water = WaterFlow(1000, 40)
cold_water = WaterFlow(1000, 25)
air = AirFlow(30, 50)
#градирня по умолчанию с NTU = 1
ct = CoolingTower(C=0.95, L_G_ratio=0.5)
ct.set_air(air)
ct.set_cold_water(cold_water)
ct.set_hot_water(hot_water)
print(ct.calculate_cold_water_temp())
print(air.wet_bulb_temperature(30, 40), air.wet_bulb_temperature_precise(30,40))