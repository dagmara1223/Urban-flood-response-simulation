import numpy as np
import rasterio
from rasterio.transform import rowcol, xy
import osmnx as ox
from rasterio.features import rasterize
from shapely.geometry import box
from pyproj import Transformer
from shapely.ops import transform as shp_transform
from pyproj import CRS
import scipy.ndimage as ndi


class FloodModel:
    def __init__(self, path_to_dem: str, k: float, area_bounds:tuple=(2000, 3200, 3500, 4800), rain_block:list=[(6,6), (12,3), (3,15), (6,4)]):
        self.height, self.transform, self.raster_crs = self.open_dem(path_to_dem)
        self.area, self.water, self.roads, self.roads_mask, self.river_mask = self.get_roads_and_rivers(area_bounds)
        self.k = k
        self.rain_series = self.get_rain_series(rain_block)
        self.current_rain_index = 0
        self.overflow_triggered = False  # sygnał czy już było przelanie
        self.river_idx = self.river_idx = np.argwhere(self.river_mask)
        self.global_min = float(np.min(self.height))
        self.global_max = float(np.max(self.height))
        self.floodplain_mask = self.build_floodplain_mask()
        self.area_bounds = area_bounds
        self.custom_overflow_mask = self.build_custom_overflow_mask()


    def step(self, t):
        # maska "miasta" = poza rzeką i poza strefą zalewową
        city_mask = ~(self.river_mask | self.floodplain_mask)

        # deszcz
        if self.current_rain_index < len(self.rain_series):
            rain_m = self.rain_series[self.current_rain_index]

            # ile deszczu zostaje na powierzchni:
            RIVER_FACTOR      = 1.0  # % opadu do Wisły
            FLOODPLAIN_FACTOR = 0.9  # % opadu zostaje na terenach zalewowych
            CITY_FACTOR       = 0.3  # tylko % opadu zostaje w mieście

            # rzeka
            self.water[self.river_mask] += rain_m * RIVER_FACTOR
            # dolina zalewowa (Płaszów / Rybitwy itp.)
            self.water[self.floodplain_mask & ~self.river_mask] += rain_m * FLOODPLAIN_FACTOR
            # reszta miasta – prawie wszystko wsiąka / idzie do kanalizacji
            self.water[city_mask] += rain_m * CITY_FACTOR

        self.current_rain_index += 1

        LOCAL_BREACH_THRESHOLD = 0.95
        LOCAL_BREACH_RATE = 0.025        # spokojniejszy, ale długotrwały
        LOCAL_BREACH_DURATION = 8       # ile kroków po przebiciu (8 × 10 min = 80 min)

        if not hasattr(self, "breach_counter"):
            self.breach_counter = 0

        river_level = np.max(self.water[self.river_mask])

        if self.rain_series[self.current_rain_index] >= 0.002 and self.rain_series[self.current_rain_index-1] < 0.002:
            self.breach_counter -= 2

        if river_level > LOCAL_BREACH_THRESHOLD and self.breach_counter < LOCAL_BREACH_DURATION:
            breach_flow = (river_level - LOCAL_BREACH_THRESHOLD) * LOCAL_BREACH_RATE

            self.water[self.custom_overflow_mask] += breach_flow
            self.water[self.river_mask] -= breach_flow * 0.20

            self.breach_counter += 1 # część wody ubywa z rzeki

        if self.current_rain_index % 2 == 0:
            self.water = self.flood_step(self.area, self.water, self.k, self.roads_mask)

        self.water[self.river_mask] = np.maximum(self.water[self.river_mask], 0.5)
        
        # drenaz miasta
        DRAINAGE_CITY = 0.0005  # 0.5 mm na krok znika w mieście
        drain_mask = city_mask & (~self.custom_overflow_mask)
        self.water[drain_mask] = np.clip(self.water[drain_mask] - DRAINAGE_CITY, 0, None)

        if t % 10 == 0:
            non_river = ~self.river_mask
            max_outside = np.max(self.water[non_river])
            count_outside = np.count_nonzero(self.water[non_river] > 0.001)

            river_total = (self.area + self.water)[self.river_mask]
            ring = ndi.binary_dilation(self.river_mask) & (~self.river_mask)
            ring_total = (self.area + self.water)[ring]

            print(f"\n[t={t}] DIAGNOSTYKA:")
            print(f"  max water poza Wisłą = {max_outside:.4f} m")
            print(f"  liczba komórek z wodą > 1 mm = {count_outside}")
            print(f"  total_level rzeka: min={river_total.min():.2f}, max={river_total.max():.2f}")
            print(f"  total_level wał:   min={ring_total.min():.2f}, max={ring_total.max():.2f}")
            local_max = np.max(self.water[self.custom_overflow_mask])
            print(f"  local breach depth = {local_max:.2f} m")

        # przelanie walow + info
        river_max_level = np.max(self.water[self.river_mask])
        OVERFLOW_THRESHOLD = 1.0  # 1 m słupa wody w korycie

        if (not self.overflow_triggered) and (river_max_level > OVERFLOW_THRESHOLD):
            print(f"overflow triggered")

            self.k = 0.25  # więcej przepływu po zalaniu

            ring = ndi.binary_dilation(self.river_mask) & (~self.river_mask)
            self.water[ring] += 0.3        # woda wylewa się na dolinę
            self.water[self.river_mask] -= 0.1

            self.overflow_triggered = True
        

    def flood_step(self, height, water, k, roads_mask):
        total = height + water
        new_water = water.copy()

        # parametry tłumienia
        MIN_FLOW = 0.01   # woda poniżej 1 cm stoi w miejscu
        FLOW_CAP = 0.5   # max % wody może wypłynąć z komórki
        FRICTION = 0.05   # opór terenu (0.0 brak oporu, 1.0 ogromny opór)

        for i in range(1, height.shape[0]-1):
            for j in range(1, height.shape[1]-1):

                if water[i,j] < MIN_FLOW:
                    continue  # za mało wody aby popłynąć

                neighbors = total[i-1:i+2, j-1:j+2]
                diff = total[i,j] - neighbors

                flow = np.clip(diff, 0, None)

                total_flow = flow.sum() - flow[1,1]
                if total_flow <= 0 or not np.isfinite(total_flow):
                    continue

                # drogi -> szybszy spływ
                #local_k = k * (1.8 if roads_mask[i,j] else 1.0)
                if self.custom_overflow_mask[i, j]:
                    local_k = k * 2.5   # zalew = szybkie, agresywne rozlewanie
                else:
                    local_k = k * (1.8 if roads_mask[i,j] else 1.0)

                # normalizacja i tłumienie
                flow_norm = (flow / total_flow) * (1.0 - FRICTION)

                # ile maksymalnie może wypłynąć
                outflow = min(local_k * water[i,j], FLOW_CAP * water[i,j])

                new_water[i,j] -= outflow
                new_water[i-1:i+2, j-1:j+2] += flow_norm * outflow

        return np.clip(new_water, 0, None)

    def select_river_section(self, x_min, x_max):
        return self.river_idx[(self.river_idx[:,1] > x_min) & (self.river_idx[:,1] < x_max)]
    def build_floodplain_mask(self):
        """
        Przybliżona strefa zalewowa:
        - piksele nisko położone (np. dolne 40% wysokości),
        - ALE tylko w sąsiedztwie Wisły (dylacja maski rzeki).
        """
        # niski teren 
        low_alt = self.area < np.percentile(self.area, 40)

        # sąsiedztwo rzeki (20 pikseli od koryta, po downsamplingu 4x)
        near_river = ndi.binary_dilation(self.river_mask, iterations=20)

        floodplain = low_alt & near_river
        return floodplain

    def build_custom_overflow_mask(self):
        mask = np.zeros_like(self.area, dtype=bool)

        # obszary dodatkowego wylewu 
        mask[650:1000,50:500] = True  

        mask[340:750, 1700:2100] = True

        padded_roads = ndi.binary_dilation(self.roads_mask, iterations=5)

        # ostateczna maska — tylko tam gdzie obszar użytkownika i powiększona droga
        mask = mask & padded_roads

        return mask
    
    def open_dem(self, dem_path: str):
        with rasterio.open(dem_path) as src:
            height = src.read(1)
            transform = src.transform   # do późniejszego odczytu piksel_size
            pix_size_x = abs(transform[0])   # [m/pixel]
            pix_size_y = abs(transform[4]) 

            raster_crs = src.crs
            if src.crs.to_epsg() is None:
                raster_crs = CRS.from_epsg(2180)  # domyślnie EPSG:2180 jeśli brak CRS
        return height, transform, raster_crs
    
    
    def get_roads_and_rivers(self, area_bounds:tuple):
        #obszar rynku 
        area = self.height[area_bounds[0]:area_bounds[1], area_bounds[2]:area_bounds[3]]
        area = area[::4, ::4]

        water = np.zeros_like(area, dtype=float)

        # ------------------ area drog --------------------------------------------------------

        r0, r1 = area_bounds[0], area_bounds[1]
        c0, c1 = area_bounds[2], area_bounds[3]

        # współrzędne geograficzne tego obszaru
        x_min, y_max = xy(self.transform, r0, c0)
        x_max, y_min = xy(self.transform, r1, c1)


        # pobieramy bounding box w DEM CRS
        bbox_poly = box(x_min, y_min, x_max, y_max)

        # pobieramy drogi w WGS84
        to_wgs84 = Transformer.from_crs(self.raster_crs, "EPSG:4326", always_xy=True).transform
        bbox_poly_wgs = shp_transform(to_wgs84, bbox_poly)

        gdf_roads = ox.features_from_polygon(bbox_poly_wgs, {"highway": True})

        # projekcja dróg do CRS DEM
        roads = gdf_roads.to_crs(self.raster_crs)
        roads["geometry"] = roads.buffer(5)

        # rasteryzacja dróg na pełny DEM 
        roads_raster_full = rasterize(
            [(geom, 1) for geom in roads.geometry],
            out_shape=self.height.shape,
            transform=self.transform,
            fill=0
        )

        # wycinek jak dla rynku - wazne - do zmiany gdy zmienia sie obszar height
        roads = roads_raster_full[area_bounds[0]:area_bounds[1], area_bounds[2]:area_bounds[3]]

        # downsampling taki jak przy glownym obszarze
        roads = roads[::4, ::4]

        # ------------------ koniec area drog ---------------------------------------------
        roads_mask = roads.astype(bool)

        # ------------------ area maski wisly ---------------------------------------------
        # pobieram wisle
        gdf_river = ox.features_from_polygon(bbox_poly_wgs, {"waterway": "river"})

        # filtr tylko wisla - nie chcemy zalapania sie innej rzeki - Vistula
        gdf_river = gdf_river[
            gdf_river.get("name", "").str.contains("Wis", case=False, na=False) |
            gdf_river.get("name", "").str.contains("Vist", case=False, na=False)
        ]

        # jeśli pusta 
        if gdf_river.empty:
            gdf_river = ox.features_from_polygon(bbox_poly_wgs, {"water": "river"})

        # projekcja do CRS DEM
        river = gdf_river.to_crs(self.raster_crs)

        # bufor – bo linia rzeki ma szerokość
        river["geometry"] = river.buffer(60)  # 15 m – można dać 20, 30 itd do zmian

        river_raster_full = rasterize(
            [(geom, 1) for geom in river.geometry],
            out_shape=self.height.shape,
            transform=self.transform,
            fill=0
        )

        # wycinek rynku
        river_rynek = river_raster_full[area_bounds[0]:area_bounds[1], area_bounds[2]:area_bounds[3]]
        river_rynek = river_rynek[::4, ::4]

        # maska wisły
        river_mask = river_rynek.astype(bool)

        # startowy poziom rzeki
        water[river_mask] = 0.50  # 50 cm wody w korycie na starcie
        # ----------------- koniec maski wisly ------------------------------------------
        return area, water, roads, roads_mask, river_mask

    def get_rain_series(self, rain_block:list):
        # dodajemy opady
        dt_seconds = 600.0  # co 10 min
        dt_hours = dt_seconds / 3600.0

        # funkcja mm/h -> metry slupa wody dodane w 1 iteracji 
        def mmph_to_m_per_iteration(mm_per_hour: float)->float:
            return (mm_per_hour / 1000.0)*dt_hours # czyli mm->m i mnozymy przez czas kroku

        rain_series = [] #seria intensywnosci per iteracja 
        for hours, mmph in rain_block:
            steps = int(np.ceil(hours / dt_hours))
            rain_series.extend([mmph_to_m_per_iteration(mmph)] * steps)

        total_mm = sum(h*mmph for h, mmph in rain_block)
        print(f"Łączny opad scenariusza = {total_mm} mm")
        return rain_series
