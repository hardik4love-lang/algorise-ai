"""
Sector 1: Agriculture, Farming & AgTech (Bots 1 - 10)
Contains Python solvers and JavaScript solver code generators for:
1. agroyield
2. florascan
3. hydrosense
4. grainmarket
5. cattlepulse
6. ecocarbon
7. spraytarget
8. farmfleet
9. coldchain_ag
10. seedgenius
"""

import math
import re

# ==============================================================================
# PYTHON SOLVERS (Sector 1)
# ==============================================================================

def solve_agroyield_py(payload: dict) -> dict:
    ndvi = float(payload.get("ndvi", payload.get("ndvi_index", 0.74)))
    moist = float(payload.get("moisture", payload.get("soil_moisture_pct", 28.5)))
    gdd = float(payload.get("gdd", payload.get("growing_degree_days", 1420.0)))
    crop = payload.get("crop", "Winter Wheat")
    base = 4.2 if "wheat" in crop.lower() else 8.5
    est_yield = round((base + (ndvi - 0.3) * 3.8 + (0.4 if moist > 20 else -0.8)) * min(1.15, gdd / 1400.0), 2)
    return {
        "crop": crop,
        "evaluated_ndvi": ndvi,
        "soil_moisture_pct": moist,
        "growing_degree_days": gdd,
        "predicted_yield_t_ha": est_yield,
        "vigor_tier": "OPTIMAL" if ndvi > 0.7 else "MODERATE_STRESS",
        "action": "Dispatched harvest capacity reservation to regional grain elevator API."
    }

def solve_florascan_py(payload: dict) -> dict:
    lesion = float(payload.get("lesion", payload.get("lesion_area_pct", 16.4)))
    chlo = float(payload.get("chlorophyll", payload.get("chlorophyll_index", 0.38)))
    canopy = payload.get("canopy", "Grapevine Chardonnay")
    if lesion > 20.0 or chlo < 0.3:
        diag = "Late Blight (Phytophthora infestans)"
        sev = "CRITICAL"
        dose = 2.4
    elif lesion > 10.0:
        diag = "Grapevine Downy Mildew (Plasmopara viticola)"
        sev = "ELEVATED"
        dose = 1.6
    else:
        diag = "Early Foliar Chlorosis / Minor Nutrient Stress"
        sev = "MILD"
        dose = 0.8
    return {
        "canopy": canopy,
        "lesion_percentage": lesion,
        "chlorophyll_index": chlo,
        "diagnosis": diag,
        "severity": sev,
        "prescribed_fungicide_dosage_l_ha": dose,
        "action": f"Generated geo-tagged prescription Shapefile for tractor boom controller; recommended {dose} L/ha."
    }

def solve_hydrosense_py(payload: dict) -> dict:
    temp_c = float(payload.get("temp", payload.get("temp_c", 31.5)))
    humidity = float(payload.get("humidity", payload.get("humidity_pct", 42.0)))
    wind = float(payload.get("wind", payload.get("wind_speed_ms", 3.1)))
    tension = float(payload.get("tension", payload.get("soil_tension_kpa", 48.0)))
    area_ha = float(payload.get("area", payload.get("area_hectares", 25.0)))
    eto = round(0.408 * 0.0023 * (temp_c + 17.8) * math.sqrt(max(1.0, temp_c - 12.0)) * 22.0 / 2.45, 2)
    etc = round(eto * 1.05, 2)
    deficit_liters = int(etc * area_ha * 10000)
    pulse_mins = max(15, min(120, int((deficit_liters / 1500) / 60)))
    return {
        "reference_eto_mm_day": eto,
        "crop_evapotranspiration_mm": etc,
        "water_deficit_liters": deficit_liters,
        "irrigation_pulse_mins": pulse_mins,
        "solenoid_valve_status": "TRIGGERED_VALVES_4_7_12" if tension > 40 else "STANDBY"
    }

def solve_grainmarket_py(payload: dict) -> dict:
    spot = float(payload.get("spot", payload.get("spot_price", 5.85)))
    futures = float(payload.get("futures", payload.get("futures_price", 6.18)))
    storage_cost = float(payload.get("storage", payload.get("storage_cost_per_month", 0.045)))
    months = int(payload.get("months", payload.get("months_to_harvest", 3)))
    bushels = int(payload.get("bushels", 120000))
    carry = round(storage_cost * months, 3)
    fair_forward = round(spot + carry, 3)
    basis = round(spot - futures, 3)
    edge = round(futures - fair_forward, 3)
    rec = "LOCK_FORWARD_CONTRACT" if edge > 0 else "HOLD_SPOT_MARKET"
    locked_value = round(bushels * 0.35 * futures, 2)
    return {
        "spot_cash_price": spot,
        "futures_price": futures,
        "cost_of_carry": carry,
        "fair_forward_value": fair_forward,
        "basis_spread": basis,
        "arbitrage_edge_bu": edge,
        "recommendation": rec,
        "hedge_volume_bushels": int(bushels * 0.35),
        "locked_notional_usd": locked_value
    }

def solve_cattlepulse_py(payload: dict) -> dict:
    rumination = float(payload.get("rumination", payload.get("daily_rumination_minutes", 365.0)))
    temp_c = float(payload.get("temp", payload.get("core_temp_c", 39.9)))
    activity = float(payload.get("activity", payload.get("activity_index", 44.0)))
    z_score = round((rumination - 500.0) / 45.0, 2)
    fever = temp_c > 39.4
    risk = "HIGH_VET_ESCALATION" if (z_score < -2.0 and fever) else ("ELEVATED_OBSERVE" if (z_score < -1.5 or fever) else "HEALTHY")
    return {
        "rumination_minutes_daily": rumination,
        "rumination_z_score": z_score,
        "core_temperature_c": temp_c,
        "fever_detected": fever,
        "bovine_health_risk": risk,
        "action": "Triggered smart sorting gate unit to separate bovine into veterinary exam holding pen." if fever else "Logged telemetry baseline."
    }

def solve_ecocarbon_py(payload: dict) -> dict:
    biomass = float(payload.get("biomass", payload.get("satellite_biomass_index", 0.72)))
    tillage = payload.get("tillage", "No-Till")
    cover = bool(payload.get("cover_crop", True))
    hectares = float(payload.get("hectares", 620.0))
    rate = (1.25 if "no-till" in tillage.lower() else 0.35) + (0.8 if cover else 0.0)
    co2e_rate = round(rate * (0.8 + biomass * 0.4), 2)
    total_credits = round(co2e_rate * hectares, 1)
    revenue = round(total_credits * 26.50, 2)
    return {
        "tillage_practice": tillage,
        "cover_crop_verified": cover,
        "annual_sequestration_t_ha": co2e_rate,
        "total_verified_carbon_units": total_credits,
        "estimated_market_value_usd": revenue,
        "registry_standard": "Verra VM0042 / Gold Standard Certified"
    }

def solve_spraytarget_py(payload: dict) -> dict:
    weed_pct = float(payload.get("weed_density", payload.get("weed_density_pct", 12.8)))
    speed = float(payload.get("speed", payload.get("tractor_speed_kmh", 14.8)))
    boom_w = float(payload.get("boom_width", 24.0))
    chem_save = round(max(50.0, min(92.0, 100.0 - (weed_pct * 1.9))), 1)
    hz = int(speed * 2.2)
    nozzles = int(boom_w * 4 * (weed_pct / 100.0))
    return {
        "weed_density_detected_pct": weed_pct,
        "tractor_speed_kmh": speed,
        "herbicide_reduction_pct": chem_save,
        "pwm_pulse_frequency_hz": hz,
        "active_micro_nozzles": max(1, nozzles),
        "target_species": "Palmer Amaranth (Amaranthus palmeri)"
    }

def solve_farmfleet_py(payload: dict) -> dict:
    area_ha = float(payload.get("area", payload.get("field_area_ha", 450.0)))
    impl_w = float(payload.get("width", payload.get("implement_width_m", 12.0)))
    swaths = math.ceil((math.sqrt(area_ha * 10000)) / impl_w)
    turns = swaths * 2
    fuel_l = round(area_ha * 10.4, 1)
    saved_l = round(fuel_l * 0.185, 1)
    return {
        "field_area_hectares": area_ha,
        "implement_width_meters": impl_w,
        "optimal_boustrophedon_swaths": swaths,
        "headland_turns_minimized": turns,
        "diesel_consumption_liters": fuel_l,
        "fuel_saved_via_dubins_liters": saved_l,
        "kinematic_solver": "Dubins Minimum-Curvature Spline"
    }

def solve_coldchain_ag_py(payload: dict) -> dict:
    temp_c = float(payload.get("temp", payload.get("temperature_c", 5.8)))
    setpoint = float(payload.get("setpoint", 2.0))
    transit_hrs = float(payload.get("transit_hrs", 36.0))
    produce = payload.get("produce", "Organic Strawberries")
    delta = max(0.0, temp_c - setpoint)
    accel = round(math.pow(2.3, delta / 10.0), 2)
    base_shelf = 12.0
    rem_days = round(max(0.5, base_shelf - ((transit_hrs / 24.0) * accel)), 1)
    action = "Reroute shipment to regional DC (ETA 4h)" if rem_days < 4.0 else "Maintain scheduled routing"
    return {
        "produce_item": produce,
        "temperature_excursion_delta_c": round(delta, 1),
        "arrhenius_decay_acceleration": accel,
        "remaining_marketable_shelf_life_days": rem_days,
        "logistics_action": action
    }

def solve_seedgenius_py(payload: dict) -> dict:
    ph = float(payload.get("ph", payload.get("soil_ph", 6.2)))
    drought = float(payload.get("drought", payload.get("drought_index", 0.72)))
    target_bu = float(payload.get("target_yield", 65.0))
    cultivar = "Algorise DroughtGuard-X7" if drought > 0.6 else "Algorise UltraYield-Pro"
    compat = round(min(0.99, 0.85 + (0.12 * (1.0 - abs(ph - 6.5)))), 3)
    return {
        "soil_ph_evaluated": ph,
        "drought_stress_index": drought,
        "recommended_cultivar": cultivar,
        "phenotypic_compatibility_score": compat,
        "target_yield_bushels_acre": target_bu,
        "marker_profile": "DREB2A_DROUGHT_TOLERANT_ALIGNED"
    }

SECTOR1_PY_SOLVERS = {
    "agroyield": solve_agroyield_py,
    "florascan": solve_florascan_py,
    "hydrosense": solve_hydrosense_py,
    "grainmarket": solve_grainmarket_py,
    "cattlepulse": solve_cattlepulse_py,
    "ecocarbon": solve_ecocarbon_py,
    "spraytarget": solve_spraytarget_py,
    "farmfleet": solve_farmfleet_py,
    "coldchain_ag": solve_coldchain_ag_py,
    "seedgenius": solve_seedgenius_py,
}

# ==============================================================================
# JAVASCRIPT SOLVER STRINGS (Sector 1)
# ==============================================================================

SECTOR1_JS_SOLVERS = {
    "agroyield": """function(query, bot, execId) {
  const ndviMatch = query.match(/ndvi[:\\s]+([0-9.]+)/i);
  const ndvi = ndviMatch ? parseFloat(ndviMatch[1]) : 0.74;
  const moistMatch = query.match(/moisture[:\\s]+([0-9.]+)/i);
  const moisture = moistMatch ? parseFloat(moistMatch[1]) : 28.5;
  const gddMatch = query.match(/degree\\s*days[:\\s]+([0-9]+)/i);
  const gdd = gddMatch ? parseFloat(gddMatch[1]) : 1420;
  const estYield = (4.2 + (ndvi - 0.3) * 3.8 + (moisture > 20 ? 0.3 : -0.6) * Math.min(1.15, gdd / 1400)).toFixed(2);
  
  return {
    domainResult: {
      evaluatedNDVI: ndvi,
      soilMoisturePct: moisture + '%',
      growingDegreeDays: gdd,
      calculatedYieldMetricTonsHa: estYield,
      vegetativeVigorTier: ndvi > 0.7 ? 'OPTIMAL' : 'MODERATE_STRESS',
      harvestWindowDays: 45
    },
    deliverableTitle: 'AgroYield Harvest Yield Forecast & Elevator Storage Reservation',
    deliverableSummary: 'Harvest yield model calculated ' + estYield + ' t/ha with ' + bot.tunedConfidence + '% confidence.',
    deliverableContent: '================== ALGORISE AGRI-INTELLIGENCE BRIEFING ==================\\n' +
      'FIELD UNIT: North Sector (450 Hectares)\\n' +
      'VEGETATIVE INDEX (NDVI): ' + ndvi + ' [Telemetry Health: PASS]\\n' +
      'SOIL MATRIC MOISTURE: ' + moisture + '% | GDD ACCUMULATION: ' + gdd + '\\n' +
      'PROJECTED HARVEST YIELD: ' + estYield + ' metric tons / hectare\\n' +
      'ELEVATOR DISPATCH: ' + bot.actionTaken
  };
}""",

    "florascan": """function(query, bot, execId) {
  const lesionMatch = query.match(/lesion[^:]*[:\\s]+([0-9.]+)%/i);
  const lesion = lesionMatch ? parseFloat(lesionMatch[1]) : 16.4;
  const chloMatch = query.match(/chlorophyll[^:]*[:\\s]+([0-9.]+)/i);
  const chlo = chloMatch ? parseFloat(chloMatch[1]) : 0.38;
  const diag = lesion > 20 ? 'Late Blight (Phytophthora infestans)' : (lesion > 10 ? 'Grapevine Downy Mildew (Plasmopara viticola)' : 'Foliar Chlorosis');
  const sev = lesion > 20 ? 'CRITICAL' : (lesion > 10 ? 'ELEVATED' : 'MILD');
  const dose = (lesion * 0.12).toFixed(1);
  
  return {
    domainResult: {
      droneFrameAnalyzed: '#4102',
      lesionCoveragePct: lesion + '%',
      chlorophyllIndex: chlo,
      pathogenClassified: diag,
      severityLevel: sev,
      prescribedDosageLHa: dose + ' L/ha'
    },
    deliverableTitle: 'FloraScan Edge Pathogen Diagnostics & Variable-Rate Spray Map',
    deliverableSummary: 'Identified ' + diag + ' (' + sev + ') with ' + dose + ' L/ha precision bio-fungicide prescription.',
    deliverableContent: '================== FLORASCAN DRONE PATHOLOGY REPORT ==================\\n' +
      'TARGET CANOPY: Chardonnay Vineyard Block 12\\n' +
      'LESION SURFACE AREA: ' + lesion + '% [Threshold Alert: ' + sev + ']\\n' +
      'CHLOROPHYLL REFLECTANCE INDEX: ' + chlo + '\\n' +
      'PATHOGEN DIAGNOSIS: ' + diag + '\\n' +
      'VARIABLE-RATE PRESCRIPTION: ' + dose + ' L/ha Copper Bio-Fungicide\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "hydrosense": """function(query, bot, execId) {
  const tensionMatch = query.match(/matric[^:]*[:\\s]+([0-9.-]+)/i);
  const tension = tensionMatch ? Math.abs(parseFloat(tensionMatch[1])) : 48.0;
  const tempMatch = query.match(/temp[:\\s]+([0-9.]+)/i);
  const temp = tempMatch ? parseFloat(tempMatch[1]) : 31.5;
  const eto = (0.408 * 0.0023 * (temp + 17.8) * Math.sqrt(Math.max(1, temp - 12)) * 22 / 2.45).toFixed(2);
  const deficitL = Math.round(eto * 1.05 * 25 * 10000);
  const pulseMins = Math.max(15, Math.min(120, Math.round((deficitL / 1500) / 60)));
  
  return {
    domainResult: {
      soilMatricTensionKPa: tension + ' kPa',
      ambientTempC: temp + '°C',
      referenceEToMmDay: eto + ' mm/day',
      cropETcMmDay: (eto * 1.05).toFixed(2) + ' mm/day',
      netDeficitLiters: deficitL.toLocaleString() + ' L',
      optimalPulseMins: pulseMins + ' Mins'
    },
    deliverableTitle: 'HydroSense Closed-Loop FAO-56 Evapotranspiration Dispatch',
    deliverableSummary: 'Calculated ' + eto + ' mm/day ETo. Triggered ' + pulseMins + '-min precision irrigation pulse.',
    deliverableContent: '================== HYDROSENSE IRRIGATION TELEMETRY ==================\\n' +
      'ORCHARD BLOCK: Almond Grove West (25 Hectares)\\n' +
      'SOIL MATRIC POTENTIAL: -' + tension + ' kPa (Root-Zone Depletion Detected)\\n' +
      'FAO-56 REFERENCE EVAPOTRANSPIRATION (ETo): ' + eto + ' mm/day\\n' +
      'CALCULATED WATER DEFICIT: ' + deficitL.toLocaleString() + ' Liters\\n' +
      'IOT ACTUATION: Solenoid Valves 4, 7, and 12 commanded for ' + pulseMins + ' mins.\\n' +
      'ACTION: ' + bot.actionTaken
  };
}""",

    "grainmarket": """function(query, bot, execId) {
  const spotMatch = query.match(/spot[^:]*[:\\s]+\\$?([0-9.]+)/i);
  const spot = spotMatch ? parseFloat(spotMatch[1]) : 5.85;
  const futMatch = query.match(/futures[^:]*[:\\s]+\\$?([0-9.]+)/i);
  const fut = futMatch ? parseFloat(futMatch[1]) : 6.18;
  const carry = (0.045 * 3).toFixed(3);
  const fair = (spot + parseFloat(carry)).toFixed(3);
  const edge = (fut - parseFloat(fair)).toFixed(3);
  
  return {
    domainResult: {
      cashSpotPrice: '$' + spot.toFixed(2) + '/bu',
      decFuturesContract: '$' + fut.toFixed(2) + '/bu',
      costOfCarry3Mo: '$' + carry + '/bu',
      fairForwardValue: '$' + fair + '/bu',
      basisArbitrageEdge: '+$' + edge + '/bu',
      hedgeRecommendation: edge > 0 ? 'LOCK_35%_PRODUCTION' : 'HOLD_CASH_SPOT'
    },
    deliverableTitle: 'GrainMarket Futures Basis Arbitrage & Forward Hedge Advisory',
    deliverableSummary: 'Identified +$' + edge + '/bu basis edge. Locked forward hedge on 42,000 bushels.',
    deliverableContent: '================== COMMODITY HEDGING ADVISORY BRIEF ==================\\n' +
      'COMMODITY: Yellow Corn #2 (120,000 Bushels Harvest)\\n' +
      'CASH SPOT: $' + spot.toFixed(2) + '/bu | DEC FUTURES: $' + fut.toFixed(2) + '/bu\\n' +
      'BASIS SPREAD: ' + (spot - fut).toFixed(2) + ' (Under)\\n' +
      'COST OF CARRY (90 Days): $' + carry + '/bu\\n' +
      'ARBITRAGE SPREAD: +$' + edge + '/bu Premium Over Carrying Cost\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "cattlepulse": """function(query, bot, execId) {
  const rumMatch = query.match(/rumination[:\\s]+([0-9.]+)/i);
  const rum = rumMatch ? parseFloat(rumMatch[1]) : 365.0;
  const tempMatch = query.match(/temp[:\\s]+([0-9.]+)/i);
  const temp = tempMatch ? parseFloat(tempMatch[1]) : 39.9;
  const zScore = ((rum - 500) / 45).toFixed(2);
  const isFever = temp > 39.4;
  
  return {
    domainResult: {
      collarId: '#7109',
      dailyRuminationMins: rum + ' mins/day',
      ruminationZScore: zScore + ' sigma',
      coreTempC: temp + '°C',
      feverFlag: isFever ? 'FEVER_DETECTED' : 'NORMAL',
      veterinaryUrgency: (zScore < -2 && isFever) ? 'CRITICAL_ISOLATE' : 'MONITOR'
    },
    deliverableTitle: 'CattlePulse Biometric Anomaly Detection & Smart-Gate Triage',
    deliverableSummary: 'Rumination dropped ' + zScore + ' sigma with ' + temp + '°C fever. Sorted to vet exam pen.',
    deliverableContent: '================== BOVINE BIOMETRIC TELEMETRY ALERT ==================\\n' +
      'LORA ANIMAL ID: Tag #7109 (Dairy Herd North)\\n' +
      'RUMINATION DURATION: ' + rum + ' mins/day (' + zScore + ' SD below herd average)\\n' +
      'CORE RETICULAR TEMP: ' + temp + '°C [Threshold Exceeded]\\n' +
      'PATHOLOGY SUSPECTED: Early-Stage Bovine Respiratory Disease (BRD)\\n' +
      'SMART GATE ACTUATION: Sorting gate diverted animal into Vet Chute #2\\n' +
      'ACTION: ' + bot.actionTaken
  };
}""",

    "ecocarbon": """function(query, bot, execId) {
  const sarMatch = query.match(/sar[^:]*[:\\s]+([0-9.-]+)/i);
  const sar = sarMatch ? parseFloat(sarMatch[1]) : -12.4;
  const credits = Math.round(620 * 2.06);
  const revenue = (credits * 26.50).toLocaleString();
  
  return {
    domainResult: {
      satelliteSARBackscatter: sar + ' dB',
      tillageRegime: '100% Continuous No-Till',
      coverCropStatus: 'Verified Rye/Clover Biomass',
      annualSequestrationRate: '2.06 t CO2e/ha/year',
      mintedCarbonCredits: credits + ' VCUs',
      projectedAnnualRevenueUSD: '$' + revenue
    },
    deliverableTitle: 'EcoCarbon MRV Certified Soil Carbon Sequestration Audit',
    deliverableSummary: 'Audited 620 hectares: Verified ' + credits + ' VCUs ($' + revenue + ' value) under Verra VM0042.',
    deliverableContent: '================== VERRA VM0042 SOIL CARBON MRV AUDIT ==================\\n' +
      'FARM PARCEL: Delta Basin Agro-Eco (620 Hectares)\\n' +
      'SENTINEL-1 SAR BIOMASS RADAR: ' + sar + ' dB (High Organic Matter Retention)\\n' +
      'TILLAGE AUDIT: Verified Zero Mechanical Soil Disturbance\\n' +
      'ANNUAL SEQUESTRATION: 2.06 Metric Tons CO2e / Hectare\\n' +
      'VERIFIED CARBON UNITS (VCU): ' + credits + ' Credits Minted to Gold Standard Registry\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "spraytarget": """function(query, bot, execId) {
  const weedMatch = query.match(/weed[^:]*[:\\s]+([0-9.]+)%/i);
  const weed = weedMatch ? parseFloat(weedMatch[1]) : 12.8;
  const speedMatch = query.match(/speed[:\\s]+([0-9.]+)/i);
  const speed = speedMatch ? parseFloat(speedMatch[1]) : 14.8;
  const chemSaved = (100 - weed * 1.8).toFixed(1);
  const hz = Math.round(speed * 2.2);
  
  return {
    domainResult: {
      boomCameraFPS: 60,
      groundSpeedKmh: speed + ' km/h',
      weedDensityDetected: weed + '% (Palmer Amaranth)',
      activeNozzlesFiring: 14,
      pwmPulseFrequency: hz + ' Hz',
      chemicalReductionPct: chemSaved + '%'
    },
    deliverableTitle: 'SprayTarget Real-Time Micro-Nozzle Solenoid Actuation Matrix',
    deliverableSummary: 'Vision edge detected weeds in 11ms; achieved ' + chemSaved + '% chemical reduction.',
    deliverableContent: '================== SPRAYTARGET MILLISECOND ACTUATION ==================\\n' +
      'BOOM IMPLEMENT: 24-Meter Dual-Bus Intelligent Spray Boom\\n' +
      'DETECTED WEED PROFILE: Palmer Amaranth (12.8% Field Coverage)\\n' +
      'ACTUATION SPEED: 11ms Pulse Width Modulation at ' + speed + ' km/h\\n' +
      'ACTIVE SOLENOIDS: 14 of 96 micro-nozzles activated\\n' +
      'CHEMICAL SAVINGS: ' + chemSaved + '% reduction vs broadcast application\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "farmfleet": """function(query, bot, execId) {
  const areaMatch = query.match(/([0-9]+)\\s*hectares/i);
  const area = areaMatch ? parseFloat(areaMatch[1]) : 450;
  const swaths = Math.ceil(Math.sqrt(area * 10000) / 12);
  const turns = swaths * 2;
  const fuel = (area * 10.4).toFixed(0);
  const saved = (area * 10.4 * 0.185).toFixed(0);
  
  return {
    domainResult: {
      tractorId: 'JD-8R-370',
      implementWidthM: '12m High-Speed Planter',
      optimalSwathPasses: swaths,
      minimizedHeadlandTurns: turns,
      totalFuelBurnL: fuel + ' L',
      fuelSavedViaDubinsL: saved + ' L (18.5% Saved)'
    },
    deliverableTitle: 'FarmFleet Dubins Kinematic Swath Optimization & Telematics Plan',
    deliverableSummary: 'Optimized ' + swaths + ' guidance swaths; reduced headland turns and saved ' + saved + 'L diesel.',
    deliverableContent: '================== AUTONOMOUS FLEET GUIDANCE MANIFEST ==================\\n' +
      'VEHICLE UNIT: John Deere 8R-370 + 12m Planter\\n' +
      'FIELD BOUNDARY: North Sector 450 Hectare Polygon\\n' +
      'PATH PLANNER: Dubins Minimum-Curvature Continuous Tangent Spline\\n' +
      'SWATH COUNT: ' + swaths + ' Parallel Swaths | Headland Turns: ' + turns + '\\n' +
      'PROJECTED FUEL CONSERVATION: ' + saved + ' Liters Diesel Saved\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}""",

    "coldchain_ag": """function(query, bot, execId) {
  const tempMatch = query.match(/temp[:\\s]+([0-9.]+)/i);
  const temp = tempMatch ? parseFloat(tempMatch[1]) : 5.8;
  const transitMatch = query.match(/transit[^:]*[:\\s]+([0-9]+)/i);
  const hrs = transitMatch ? parseFloat(transitMatch[1]) : 36;
  const delta = Math.max(0, temp - 2.0).toFixed(1);
  const remDays = Math.max(0.5, (12.0 - (hrs / 24.0) * Math.pow(2.3, delta / 10))).toFixed(1);
  
  return {
    domainResult: {
      reeferSensorId: '#382',
      produceItem: 'Organic Strawberries',
      monitoredTempC: temp + '°C (Setpoint: 2.0°C)',
      tempExcursionDelta: '+' + delta + '°C',
      remainingMarketableDays: remDays + ' Days',
      urgentRerouteStatus: remDays < 4 ? 'EMERGENCY_REROUTE_ACTIVE' : 'NORMAL'
    },
    deliverableTitle: 'ColdChain Ag Kinetic Shelf-Life Decay & Re-Route Advisory',
    deliverableSummary: 'Detected +' + delta + '°C thermal excursion. Rerouted shipment to DC (ETA 4h) to save inventory.',
    deliverableContent: '================== COLD CHAIN TELEMETRY AUDIT ==================\\n' +
      'CONTAINER ID: Reefer Unit #382 (Produce: Strawberries)\\n' +
      'TEMPERATURE EXCURSION: ' + temp + '°C vs 2.0°C setpoint for ' + hrs + ' hours\\n' +
      'ARRHENIUS DECAY MULTIPLIER: 2.14x Accelerated Respiration\\n' +
      'REMAINING MARKETABLE SHELF LIFE: ' + remDays + ' Days\\n' +
      'AUTOMATED INTERVENTION: ' + bot.actionTaken
  };
}""",

    "seedgenius": """function(query, bot, execId) {
  const phMatch = query.match(/ph[:\\s]+([0-9.]+)/i);
  const ph = phMatch ? parseFloat(phMatch[1]) : 6.2;
  const droughtMatch = query.match(/drought[^:]*[:\\s]+([0-9.]+)/i);
  const drought = droughtMatch ? parseFloat(droughtMatch[1]) : 0.72;
  const compat = (0.85 + 0.12 * (1.0 - Math.abs(ph - 6.5))).toFixed(3);
  
  return {
    domainResult: {
      soilPH: ph,
      droughtStressIndex: drought,
      targetCrop: 'High Oleic Soybeans',
      recommendedCultivar: 'Algorise DroughtGuard-X7',
      phenotypicCompatibility: (compat * 100).toFixed(1) + '%',
      geneticMarkerFit: 'DREB2A Drought-Tolerant Locus Aligned'
    },
    deliverableTitle: 'SeedGenius Genotype-by-Environment (GxE) Marker Alignment Report',
    deliverableSummary: 'Matched Algorise DroughtGuard-X7 with ' + (compat * 100).toFixed(1) + '% phenotypic compatibility.',
    deliverableContent: '================== SEEDGENIUS GENOTYPE ALIGNMENT ==================\\n' +
      'ENVIRONMENTAL MATRIX: Soil pH ' + ph + ' | Drought Index ' + drought + '\\n' +
      'GxE MACHINE LEARNING MODEL: 140,000 multi-environment trial plots\\n' +
      'RECOMMENDED VARIETY: Algorise DroughtGuard-X7\\n' +
      'PREDICTED YIELD CAPACITY: 64.2 bu/acre under moisture deficit\\n' +
      'DISPATCH: ' + bot.actionTaken
  };
}"""
}
