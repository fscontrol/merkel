import math
CP_WATER = 4.186
CP_AIR = 1.006
CP_VAPOR = 1.86
EVAPORATION_HEAT = 2501
class AirFlow:
    def __init__(self, temp, rh, pressure=101.325):
        ''' humidity 0..100'''
        self.temp = temp
        self.rh = rh
        self.pressure = pressure
    def saturation_pressure(self, T: float) -> float:
        """
        Давление насыщенного пара воды
        Формула Магнуса (Tetens formula)
        """
        # Формула: Ps = 0.61094 * exp(17.625 * T / (T + 243.04))
        # Результат в кПа
        import math
        return 0.61094 * math.exp(17.625 * T / (T + 243.04))
    
    def wet_bulb_temperature(self, T_dry, RH, P = 101.325):
        """Расчет температуры влажного термометра"""
        if not (0 <= RH <= 100):
            raise ValueError("Относительная влажность должна быть от 0 до 100%")
        if P <= 0:
            raise ValueError("Давление должно быть положительным")
        T_wb = (T_dry * math.atan(0.151977 * math.sqrt(RH + 8.313659)) + 
                math.atan(T_dry + RH) - 
                math.atan(RH - 1.676331) + 
                0.00391838 * (RH**1.5) * math.atan(0.023101 * RH) - 
                4.686035)
        return T_wb
    def wet_bulb_temperature_precise(self, T_dry, RH):
        h = self.enthalpy(T_dry, self.humidity_ratio(T_dry, RH))
        t_min = -50
        t_max = T_dry
        for i in range(100):
            t = (t_min + t_max)/2
            hc = self.enthalpy(t, self.saturation_humidity_ratio(t))
            error = abs(hc - h)
            if error < 0.01:
                break
            if hc > h:
                t_max = t 
            else:
                t_min = t 
        return t 
    def enthalpy(self, T, humidity_ratio):
        """Энтальпия влажного воздуха, кДж/кг"""
        return CP_AIR * T + humidity_ratio * (EVAPORATION_HEAT+ CP_VAPOR* T)
    
    def humidity_ratio(self, T, RH, P = 101.325):
        """Влагосодержание воздуха, кг/кг"""
        Ps = self.saturation_pressure(T)
        Pv = (RH / 100) * Ps
        return 0.622 * Pv / (P - Pv)
    
    def saturation_humidity_ratio(self, T, P = 101.325):
        """Влагосодержание насыщенного воздуха, кг/кг"""
        Ps = self.saturation_pressure(T)
        return 0.622 * Ps / (P - Ps)

class WaterFlow:
    def __init__(self, flow, temp):
        self.flow = flow
        self.temp = temp 
    def enthalpy(self, temp):
        return CP_WATER*temp    

class CoolingTower: 
    def __init__(self, C = 1.0, N = -0.55, L_G_ratio = 1.0):
        self.C = C
        self.N = N
        self.L_G_ratio = L_G_ratio
    def set_hot_water(self, hw):
        self.hot_water = hw 
    def set_cold_water(self, cw):
        self.cold_water = cw 
    def set_air(self, a):
        self.air = a 
    def calculate_merkel(self):
        h_in = self.air.enthalpy(self.air.temp, self.air.humidity_ratio(self.air.temp, self.air.rh))
        n = 100
        dT = (self.hot_water.temp - self.cold_water.temp) / n
        integral = 0
        for i in range(n + 1):
            T_w = self.hot_water.temp - i * dT
            h_s = self.air.enthalpy(T_w, self.air.saturation_humidity_ratio(T_w))
            h_a = h_in + (self.L_G_ratio * CP_WATER * (T_w - self.cold_water.temp))
            driving_force = h_s - h_a
            if driving_force <= 0:
                raise ValueError(f"Отрицательная движущая сила при T={T_w:.1f}°C")
            integrand = CP_WATER / driving_force
            if i == 0 or i == n:
                coef = 1
            elif i % 2 == 1:
                coef = 4
            else:
                coef = 2
            integral += coef * integrand
        return (integral * dT / 3)
    
    def calculate_merkel_number(self):
        return self.C * (self.L_G_ratio ** self.N)
    
    def calculate_cold_water_temp(self, tolerance: float = 0.01, max_iterations: int = 50) -> float:
        T_wb = self.air.wet_bulb_temperature(self.air.temp, self.air.rh, self.air.pressure)
        T_cold_min = T_wb + 0.5
        T_cold_max = self.hot_water.temp - 0.5
        cold_water = WaterFlow(self.hot_water.flow, T_cold_min)
        self.set_cold_water(cold_water)
        merkel_target = self.calculate_merkel_number()
        for iteration in range(max_iterations):
            self.cold_water.temp = (T_cold_min + T_cold_max) / 2
            try:
                merkel_calc = self.calculate_merkel()
            except ValueError:
                T_cold_min = self.cold_water.temp
                continue
            error = merkel_calc - merkel_target
            if abs(error) < tolerance * merkel_target:
                return self.cold_water.temp
            if merkel_calc > merkel_target:
                T_cold_min = self.cold_water.temp
            else:
                T_cold_max = self.cold_water.temp
        raise ValueError(f"Не удалось сойтись за {max_iterations} итераций")
    def calculate_evaporation(self, air_out_rh = 100):
        w_in = self.air.humidity_ratio(self.air.temp, self.air.rh, self.air.pressure)
        h_in = self.air.enthalpy(self.air.temp, w_in)
        air_flow = self.hot_water.flow/self.L_G_ratio
        h_out = h_in + CP_WATER*(self.hot_water.temp - self.cold_water.temp)*self.L_G_ratio
        t_out_min = min(self.cold_water.temp,self.air.wet_bulb_temperature(self.air.temp, self.air.rh))
        t_out_max = max(self.hot_water.temp, self.air.temp)
        for i in range(100):
            t_out = (t_out_max + t_out_min)/2
            h_calc = self.air.enthalpy(t_out, self.air.humidity_ratio(t_out, air_out_rh))
            error = abs((h_calc - h_out)/h_out) 
            print(t_out, h_calc, h_out, error)
            if error < 0.001:
                break 
            if h_calc < h_out:
                t_out_min = t_out 
            else:
                t_out_max = t_out 
        t_air_out = t_out
        return air_flow*(self.air.humidity_ratio(t_air_out, air_out_rh) - self.air.humidity_ratio(self.air.temp, self.air.rh))