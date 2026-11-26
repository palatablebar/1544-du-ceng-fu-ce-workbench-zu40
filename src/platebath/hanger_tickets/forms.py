from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class HangerTicketsSheet:
    bath_milliamperes: Decimal
    bath_seconds: Decimal
    ph_cent: Decimal
    hanger_square_cm: Decimal
    cartridge_hours: Decimal
    liquid_deci_c: Decimal

    def fields(self):
        return {
            'amps': float(self.bath_milliamperes) / 1000,
            'time_sec': float(self.bath_seconds),
            'ph_tenth': float(self.ph_cent) / 10,
            'area_dm': float(self.hanger_square_cm) / 100,
            'filter_days': float(self.cartridge_hours) / 24,
            'bath_c': float(self.liquid_deci_c) / 10,
        }

    def validation(self):
        fields = self.fields()
        amps = fields['amps']
        time_sec = fields['time_sec']
        ph_tenth = fields['ph_tenth']
        area_dm = fields['area_dm']
        filter_days = fields['filter_days']
        bath_c = fields['bath_c']
        charge_density = amps*time_sec/area_dm
        warm_acid = (ph_tenth < 41 and bath_c>59)
        filter_window = filter_days*24
        process_limit = amps/(area_dm*4.4)
        alerts = []
        if charge_density>3300:
            alerts.append(('hanger_square_cm', 'UNUSUAL_COATING_CHARGE'))
        if warm_acid and filter_window>600:
            alerts.append(('ph_cent', 'SOLUTION_CHECK_DUE'))
        if process_limit>1.9:
            alerts.append(('bath_milliamperes', 'HANGER_CURRENT_UNSUPPORTED'))
        return tuple(alerts)


def read_hanger_tickets(form):
    return HangerTicketsSheet(
        bath_milliamperes=form_number(form, '整流电源', 'bath_milliamperes', 60000, 260000),
        bath_seconds=form_number(form, '整流电源', 'bath_seconds', 80, 450),
        ph_cent=form_number(form, '挂具进槽', 'ph_cent', 350, 660),
        hanger_square_cm=form_number(form, '挂具进槽', 'hanger_square_cm', 2500, 18300),
        cartridge_hours=form_number(form, '槽液抄表', 'cartridge_hours', 0, 768),
        liquid_deci_c=form_number(form, '槽液抄表', 'liquid_deci_c', 350, 680),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_hanger_tickets(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('amps', 'time_sec', 'ph_tenth', 'area_dm', 'filter_days', 'bath_c')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
