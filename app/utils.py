from enum import Enum
import math
import logging
import requests
import os
from models.recommendation_model import Strategy, Weather, Recommendation
from fastapi import HTTPException
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Compound(Enum):
    SOFT = 1
    MEDIUM = 2
    HARD = 3


TEMP_FACTOR = {
    Compound.SOFT: 1 / (3),
    Compound.MEDIUM: 1 / (6**2),
    Compound.HARD: 1 / (7**3),
}
COMPOUND_BEST_LAP = {Compound.SOFT: 90, Compound.MEDIUM: 91, Compound.HARD: 92}


def degradation_factor(temp, compound):
    if temp < 1:
        temp = 1
    return round((temp * TEMP_FACTOR[compound]) + (math.log(temp, 10)), 2)


def lap_time(deg_factor, compound, lap):
    return COMPOUND_BEST_LAP[compound] + (deg_factor * ((lap**2) / 1000))



def strategy_min(strategy_times: List[Strategy]) -> Strategy:
    quickest_strategy = min(
        strategy_times, key=lambda strategy_times: strategy_times.race_time
    )
    return quickest_strategy


def compound_optimal(tire_1,tire_2,laps,temp):
    strategy_times = []
    deg_1 = degradation_factor(temp,tire_1)
    deg_2 = degradation_factor(temp,tire_2)
    for pit_stop in range(1,laps-1):
        race_time = 0
        for lap in range(0, laps):
            if lap < pit_stop:
                race_time += lap_time(deg_1, tire_1, lap)
            else:
                race_time += lap_time(deg_2, tire_2, lap)
        strategy = Strategy(compound_1=tire_1.name,
                            compound_2=tire_2.name,
                            pit_lap=pit_stop,
                            race_time=race_time)
        strategy_times.append(strategy)
    return strategy_min(strategy_times)
    

def best_strategy(temp, laps):
    strategy_times = []
    for tire_1 in Compound:
        for tire_2 in Compound:
            if tire_1 != tire_2:
                best_strategy = compound_optimal(tire_1,tire_2,laps,temp)
                strategy_times.append(best_strategy)
    return strategy_min(strategy_times)


def celsius_convert(temp):
    return (temp - 32) * 5.0 / 9.0


def request_wrapper(city, laps):
    api_key = os.getenv("API_KEY")
    url = f"http://api.weatherstack.com/current?access_key={api_key}&query={city}"
    try:
        response = requests.request("GET", url)
        if 'error' in response.json().keys():
            raise HTTPException(status_code=400,detail={
                "info": response.json()['error']['type']
                })
        weather = Weather(current=response.json()["current"])
        temperature = weather.current["temperature"]
        strategy = best_strategy(temperature, laps)
        recommendation = Recommendation(strategy=strategy, weather=weather)
        return recommendation
    except Exception as e:
        logging.error(f"Error-{e}-Request: for {city} failed")
        raise(e)
