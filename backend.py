import json
from datetime import datetime
from itertools import zip_longest
from pathlib import Path
from typing import Tuple

from prettytable import PrettyTable


class Backend:

    def __init__(self, people: Tuple[str], logbook_path: str, currency: str,
                 distance_units: str, volume_units: str):
        self.people = people
        self.logbook_path = Path(logbook_path)
        self.currency = currency
        self.distance_units = distance_units
        self.volume_units = volume_units
        if self.logbook_path.exists():
            with open(self.logbook_path, 'r') as f:
                self.full_logbook = json.load(f)
        else:
            self.full_logbook = []
            self.new_period()

    @property
    def current_period(self):
        return self.full_logbook[-1]

    def reset_period(self):
        self.full_logbook.pop()
        self.new_period()

    def new_period(self):
        self.full_logbook.append({p: list() for p in self.people})
        self.dump_logbook()

    def dump_logbook(self):
        with open(self.logbook_path, 'w') as f:
            json.dump(self.full_logbook, f, indent=4)

    def settle_bill(self, person, mileage, bill, fuel_consumption=None):
        ret = ''
        personal_mileage = {
            p: sum(trips)
            for p, trips in self.current_period.items()
        }
        neutral_mileage = max(0, mileage - sum(personal_mileage.values()))
        per_km_cost = bill / mileage
        neutral_cost = (neutral_mileage * per_km_cost) / len(personal_mileage)
        personal_cost = {
            p: mileage_ * per_km_cost + neutral_cost
            for p, mileage_ in personal_mileage.items()
        }
        for person_, cost in personal_cost.items():
            if person_ != person:
                ret += f'\n{person_} owes {person} {cost:.02f} {self.currency}'
        if fuel_consumption is not None:
            ret += f'\Average consumption: {fuel_consumption / (mileage / 100):.02f} {self.volume_units}/100 {self.distance_units}'
            self.current_period['Consumption'] = fuel_consumption
        self.current_period['Person_who_paid'] = person
        self.current_period['Cost'] = bill
        self.current_period['Mileage_total'] = mileage
        self.current_period['Date'] = datetime.today().strftime('%d.%m.%Y')
        self.new_period()
        return ret

    def add_mileage(self, person, mileage):
        self.current_period[person].append(mileage)
        self.dump_logbook()

    def current_logbook_as_str(self):
        table = PrettyTable()
        table.field_names = self.people
        max_rows = max([len(trips) for trips in self.current_period.values()])
        for i, row in enumerate(
                zip_longest(*list(self.current_period.values()),
                            fillvalue="")):
            table.add_row(row, divider=True if i == max_rows - 1 else False)
        table.add_row([sum(trips) for trips in self.current_period.values()])
        return '```\n' + table.get_string() + '\n```'

    def get_total_mileage_and_cost_str(self):
        total_mileage = 0
        total_cost = 0
        for period in self.full_logbook:
            total_cost += period.get('Cost', 0)
            total_mileage += period.get('Mileage_total', 0)
        return f'Total: {total_mileage} {self.distance_units} and {total_cost} {self.currency}'


if __name__ == '__main__':
    backend = Backend(people=('Eve', 'Bob'),
                      logbook_path="logbook.json",
                      currency="EUR",
                      distance_units="km",
                      volume_units="l")
    backend.reset_period()
    backend.add_mileage('Eve', 100)
    backend.add_mileage('Bob', 400)
    backend.add_mileage('Bob', 300)
    print(backend.current_logbook_as_str())
    print(backend.settle_bill('Bob', 1000, 100))
    print(backend.get_total_mileage_and_cost_str())
