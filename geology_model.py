import numpy as np
import random

# Geologically inspired color palette
GEO_COLORS = [
    "#F4A460", "#D2B48C", "#DEB887", "#D3D3D3", "#BC8F8F",
    "#A0522D", "#8B4513", "#A52A2A", "#8FBC8F", "#BDB76B",
    "#CD853F", "#C0C0C0", "#778899", "#808080", "#483D8B"
]

class Layer:
    def __init__(self, name, bottom, top, color, erosion_resistance):
        self.name = name
        self.bottom = bottom
        self.top = top
        self.color = color
        self.erosion_resistance = erosion_resistance

class SimulationEngine:
    def __init__(self, num_layers, resistances_list, thicknesses_list=None):
        self.num_layers = num_layers
        self.resistances_list = resistances_list
        self.thicknesses_list = thicknesses_list if thicknesses_list else [1.0] * num_layers
        self.res_max = 30.0
        
        self.time_elapsed = 0.0
        self.uplift_m = 0.0
        self.incision_m = 0.0  # Physical depth of the V notch
        
        self.SCALE_FACTOR = 100
        self.total_thickness = 250.0 
        self.layers = self._generate_layers()
        
    def _generate_layers(self):
        layers = []
        
        # Calculate proportional thicknesses
        valid_thicknesses = self.thicknesses_list[:self.num_layers]
        total_relative_thickness = sum(valid_thicknesses)
        if total_relative_thickness <= 0: 
            total_relative_thickness = 1.0
            valid_thicknesses = [1.0] * self.num_layers
            
        current_bottom = 0.0
        # Create layers from bottom to top
        for i in range(self.num_layers):
            rel_thick = valid_thicknesses[i] if i < len(valid_thicknesses) else 1.0
            actual_thickness = (rel_thick / total_relative_thickness) * self.total_thickness
            
            bottom = current_bottom
            top = current_bottom + actual_thickness
            
            # Distribute colors
            color = GEO_COLORS[i % len(GEO_COLORS)]
            resistance = self.resistances_list[i] if i < len(self.resistances_list) else 1.0
            name = f"Layer {i+1} (Res: {resistance:.1f}, Thick: {actual_thickness:.0f}m)"
            layers.append(Layer(name, bottom, top, color, resistance))
            
            current_bottom = top
            
        return layers

    def step(self, dt, uplift_rate_mm_yr, global_incision_rate_mm_yr):
        # 1. Apply tectonic uplift to the entire block
        self.uplift_m += (uplift_rate_mm_yr * dt * self.SCALE_FACTOR)
        
        # 2. Determine river incision speed
        # The river base relative to the bottom of the original 250m block
        relative_river_y = self.total_thickness - self.incision_m
        
        current_resistance = 1.0
        for layer in self.layers:
            if layer.bottom <= relative_river_y <= layer.top:
                current_resistance = layer.erosion_resistance
                break
                
        # If it has cut entirely through the known block, assume basement rock resistance
        if relative_river_y < 0:
            current_resistance = self.res_max 
            
        # The equation for incision depending on resistance factor
        # Higher resistance slows down the incision rate significantly.
        effective_incision_rate = global_incision_rate_mm_yr / current_resistance
        
        self.incision_m += (effective_incision_rate * dt * self.SCALE_FACTOR)
        self.time_elapsed += dt
        
    def get_terrain_profile(self, x_array):
        """
        Calculates the topological Y coordinates of the ground surface for a given array of X coords.
        This algorithm computes stepped canyon walls: hard rock -> steep cliff, soft rock -> shallow slope.
        """
        v_bottom_rel = self.total_thickness - self.incision_m
        
        # If the river hasn't cut anything, return a flat plateau
        if self.incision_m <= 0:
            max_h = self.total_thickness + self.uplift_m
            return np.full_like(x_array, max_h)
            
        # Build the right-half of the canyon wall piecewise
        y_vals = [v_bottom_rel]
        x_vals = [0.0]
        
        current_y = v_bottom_rel
        current_x = 0.0
        dy = 1.0  # 1-meter vertical increments for high resolution
        
        while current_y < self.total_thickness:
            # Determine resistance of rock at this elevation
            res = 1.0
            for l in self.layers:
                if l.bottom <= current_y <= l.top:
                    res = l.erosion_resistance
                    break
            if current_y < 0: 
                res = self.res_max
                
            # Resistance governs slope. 
            # High resistance (hard rock) -> steep wall -> dx is small.
            # Low resistance (soft rock) -> shallow wall -> dx is large.
            # Using 1.5 as a baseline width multiplier.
            dx = dy * (1.5 / res) 
            
            current_x += dx
            current_y += dy
            
            y_vals.append(current_y)
            x_vals.append(current_x)
            
        # Cap the edges of the plateau
        y_vals.append(self.total_thickness)
        x_vals.append(5000.0) # Extend infinitely to the right
        
        # Interpolate the Y profile for the requested symmetric X coordinates
        abs_x = np.abs(x_array)
        y_rel_interp = np.interp(abs_x, x_vals, y_vals)
        
        # Add absolute tectonic uplift
        y_abs = y_rel_interp + self.uplift_m
        return y_abs
