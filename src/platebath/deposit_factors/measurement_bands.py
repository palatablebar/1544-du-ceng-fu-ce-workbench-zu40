from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_current_flux(vector):
    amps = vector.input_values[0]
    area_dm = vector.input_values[3]
    return float(amps/area_dm)


def compare_current_flux(training, target):
    usual_current_flux = take_sample(training, current_current_flux)
    recent_current_flux = take_sample(target, current_current_flux)
    if len(usual_current_flux) < 4 or not recent_current_flux:
        return {'作业量': '挂件电流密度', '有效读数': len(recent_current_flux), '判断': '参考不足'}
    anchor_current_flux = median(usual_current_flux)
    measured_current_flux = median(recent_current_flux)
    band_current_flux = max(1.0, abs(anchor_current_flux)*.2, median(abs(value-anchor_current_flux) for value in usual_current_flux))
    change_current_flux = (measured_current_flux-anchor_current_flux) / band_current_flux
    outside_current_flux = sum(abs(value-anchor_current_flux)>2.5*band_current_flux for value in recent_current_flux)
    return {'作业量': '挂件电流密度', '训练参考': round(anchor_current_flux, 4), '现场中位': round(measured_current_flux, 4),
            '变动': round(change_current_flux, 4), '越界量': outside_current_flux, '有效读数': len(recent_current_flux)}


def current_coulomb_area(vector):
    amps = vector.input_values[0]
    time_sec = vector.input_values[1]
    area_dm = vector.input_values[3]
    return float(amps*time_sec/area_dm)


def compare_coulomb_area(training, target):
    usual_coulomb_area = take_sample(training, current_coulomb_area)
    recent_coulomb_area = take_sample(target, current_coulomb_area)
    if len(usual_coulomb_area) < 4 or not recent_coulomb_area:
        return {'作业量': '每平方分米库仑', '有效读数': len(recent_coulomb_area), '判断': '参考不足'}
    anchor_coulomb_area = median(usual_coulomb_area)
    measured_coulomb_area = median(recent_coulomb_area)
    band_coulomb_area = max(1.0, abs(anchor_coulomb_area)*.2, median(abs(value-anchor_coulomb_area) for value in usual_coulomb_area))
    change_coulomb_area = (measured_coulomb_area-anchor_coulomb_area) / band_coulomb_area
    outside_coulomb_area = sum(abs(value-anchor_coulomb_area)>2.5*band_coulomb_area for value in recent_coulomb_area)
    return {'作业量': '每平方分米库仑', '训练参考': round(anchor_coulomb_area, 4), '现场中位': round(measured_coulomb_area, 4),
            '变动': round(change_coulomb_area, 4), '越界量': outside_coulomb_area, '有效读数': len(recent_coulomb_area)}


def current_warm_minutes(vector):
    time_sec = vector.input_values[1]
    bath_c = vector.input_values[5]
    return float(max(0,bath_c-49)*time_sec/60)


def compare_warm_minutes(training, target):
    usual_warm_minutes = take_sample(training, current_warm_minutes)
    recent_warm_minutes = take_sample(target, current_warm_minutes)
    if len(usual_warm_minutes) < 4 or not recent_warm_minutes:
        return {'作业量': '高于基准的温时', '有效读数': len(recent_warm_minutes), '判断': '参考不足'}
    anchor_warm_minutes = median(usual_warm_minutes)
    measured_warm_minutes = median(recent_warm_minutes)
    ordered_warm_minutes = sorted(usual_warm_minutes)
    low_warm_minutes, high_warm_minutes = ordered_warm_minutes[len(ordered_warm_minutes)//10], ordered_warm_minutes[(len(ordered_warm_minutes)*9)//10]
    change_warm_minutes = measured_warm_minutes-anchor_warm_minutes
    outside_warm_minutes = sum(value<low_warm_minutes or value>high_warm_minutes for value in recent_warm_minutes)
    return {'作业量': '高于基准的温时', '训练参考': round(anchor_warm_minutes, 4), '现场中位': round(measured_warm_minutes, 4),
            '变动': round(change_warm_minutes, 4), '越界量': outside_warm_minutes, '有效读数': len(recent_warm_minutes)}


def current_ph_alkali(vector):
    ph_tenth = vector.input_values[2]
    return float(max(0,ph_tenth-49)/10)


def compare_ph_alkali(training, target):
    usual_ph_alkali = take_sample(training, current_ph_alkali)
    recent_ph_alkali = take_sample(target, current_ph_alkali)
    if len(usual_ph_alkali) < 4 or not recent_ph_alkali:
        return {'作业量': '高酸碱度方向', '有效读数': len(recent_ph_alkali), '判断': '参考不足'}
    anchor_ph_alkali = median(usual_ph_alkali)
    measured_ph_alkali = median(recent_ph_alkali)
    ordered_ph_alkali = sorted(usual_ph_alkali)
    low_ph_alkali, high_ph_alkali = ordered_ph_alkali[len(ordered_ph_alkali)//10], ordered_ph_alkali[(len(ordered_ph_alkali)*9)//10]
    change_ph_alkali = measured_ph_alkali-anchor_ph_alkali
    outside_ph_alkali = sum(value<low_ph_alkali or value>high_ph_alkali for value in recent_ph_alkali)
    return {'作业量': '高酸碱度方向', '训练参考': round(anchor_ph_alkali, 4), '现场中位': round(measured_ph_alkali, 4),
            '变动': round(change_ph_alkali, 4), '越界量': outside_ph_alkali, '有效读数': len(recent_ph_alkali)}


def current_ph_acid(vector):
    ph_tenth = vector.input_values[2]
    return float(max(0,49-ph_tenth)/10)


def compare_ph_acid(training, target):
    usual_ph_acid = take_sample(training, current_ph_acid)
    recent_ph_acid = take_sample(target, current_ph_acid)
    if len(usual_ph_acid) < 4 or not recent_ph_acid:
        return {'作业量': '低酸碱度方向', '有效读数': len(recent_ph_acid), '判断': '参考不足'}
    anchor_ph_acid = median(usual_ph_acid)
    measured_ph_acid = median(recent_ph_acid)
    band_ph_acid = max(1.0, abs(anchor_ph_acid)*.2, median(abs(value-anchor_ph_acid) for value in usual_ph_acid))
    change_ph_acid = (measured_ph_acid-anchor_ph_acid) / band_ph_acid
    outside_ph_acid = sum(abs(value-anchor_ph_acid)>2.5*band_ph_acid for value in recent_ph_acid)
    return {'作业量': '低酸碱度方向', '训练参考': round(anchor_ph_acid, 4), '现场中位': round(measured_ph_acid, 4),
            '变动': round(change_ph_acid, 4), '越界量': outside_ph_acid, '有效读数': len(recent_ph_acid)}


def current_bath_service(vector):
    filter_days = vector.input_values[4]
    return float(32-filter_days)


def compare_bath_service(training, target):
    usual_bath_service = take_sample(training, current_bath_service)
    recent_bath_service = take_sample(target, current_bath_service)
    if len(usual_bath_service) < 4 or not recent_bath_service:
        return {'作业量': '滤芯剩余巡查天数', '有效读数': len(recent_bath_service), '判断': '参考不足'}
    anchor_bath_service = median(usual_bath_service)
    measured_bath_service = median(recent_bath_service)
    ordered_bath_service = sorted(usual_bath_service)
    low_bath_service, high_bath_service = ordered_bath_service[len(ordered_bath_service)//10], ordered_bath_service[(len(ordered_bath_service)*9)//10]
    change_bath_service = measured_bath_service-anchor_bath_service
    outside_bath_service = sum(value<low_bath_service or value>high_bath_service for value in recent_bath_service)
    return {'作业量': '滤芯剩余巡查天数', '训练参考': round(anchor_bath_service, 4), '现场中位': round(measured_bath_service, 4),
            '变动': round(change_bath_service, 4), '越界量': outside_bath_service, '有效读数': len(recent_bath_service)}


def current_area_minutes(vector):
    time_sec = vector.input_values[1]
    area_dm = vector.input_values[3]
    return float(area_dm*time_sec/60)


def compare_area_minutes(training, target):
    usual_area_minutes = take_sample(training, current_area_minutes)
    recent_area_minutes = take_sample(target, current_area_minutes)
    if len(usual_area_minutes) < 4 or not recent_area_minutes:
        return {'作业量': '挂具面积浸镀积', '有效读数': len(recent_area_minutes), '判断': '参考不足'}
    anchor_area_minutes = median(usual_area_minutes)
    measured_area_minutes = median(recent_area_minutes)
    band_area_minutes = max(1.0, abs(anchor_area_minutes)*.2, median(abs(value-anchor_area_minutes) for value in usual_area_minutes))
    change_area_minutes = (measured_area_minutes-anchor_area_minutes) / band_area_minutes
    outside_area_minutes = sum(abs(value-anchor_area_minutes)>2.5*band_area_minutes for value in recent_area_minutes)
    return {'作业量': '挂具面积浸镀积', '训练参考': round(anchor_area_minutes, 4), '现场中位': round(measured_area_minutes, 4),
            '变动': round(change_area_minutes, 4), '越界量': outside_area_minutes, '有效读数': len(recent_area_minutes)}


def current_current_headroom(vector):
    amps = vector.input_values[0]
    area_dm = vector.input_values[3]
    return float(4.4*area_dm-amps)


def compare_current_headroom(training, target):
    usual_current_headroom = take_sample(training, current_current_headroom)
    recent_current_headroom = take_sample(target, current_current_headroom)
    if len(usual_current_headroom) < 4 or not recent_current_headroom:
        return {'作业量': '工艺电流裕量', '有效读数': len(recent_current_headroom), '判断': '参考不足'}
    anchor_current_headroom = median(usual_current_headroom)
    measured_current_headroom = median(recent_current_headroom)
    ordered_current_headroom = sorted(usual_current_headroom)
    low_current_headroom, high_current_headroom = ordered_current_headroom[len(ordered_current_headroom)//10], ordered_current_headroom[(len(ordered_current_headroom)*9)//10]
    change_current_headroom = measured_current_headroom-anchor_current_headroom
    outside_current_headroom = sum(value<low_current_headroom or value>high_current_headroom for value in recent_current_headroom)
    return {'作业量': '工艺电流裕量', '训练参考': round(anchor_current_headroom, 4), '现场中位': round(measured_current_headroom, 4),
            '变动': round(change_current_headroom, 4), '越界量': outside_current_headroom, '有效读数': len(recent_current_headroom)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_deposit_factors_band(history, daybook):
    yield compare_current_flux(history, daybook)
    yield compare_coulomb_area(history, daybook)
    yield compare_warm_minutes(history, daybook)
    yield compare_ph_alkali(history, daybook)
    yield compare_ph_acid(history, daybook)
    yield compare_bath_service(history, daybook)
    yield compare_area_minutes(history, daybook)
    yield compare_current_headroom(history, daybook)


def evaluate_shift(training, current):
    return list(measure_deposit_factors_band(training, current))
