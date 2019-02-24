from collections import defaultdict, namedtuple
from icalendar import Event, Calendar
from bs4 import BeautifulSoup
from itertools import count
from textwrap import fill
from sys import stderr
import requests
import datetime
import os


strptime = datetime.datetime.strptime


URL = 'https://www.lovewithingtonbaths.com/classes/'
STUDIO_DIV = 'studiosContainer'
PARSER = 'html.parser'
INCLUDED_COST = '£5*'
ROW_CLASS = 'row'
TIME_SEP = ' - '
SUCCESS = 200
WIDTH = 80

DAYS_TO_OFFSET = dict(zip(
    (
        'Monday', 'Tuesday', 'Wednesday', 'Thursday',
        'Friday', 'Saturday', 'Sunday'
    ),
    count()
))

STUDIO_LOOKUP = {
    'light1': 'Studio 1',
    'light2': 'Studio 2',
    'light3': 'Pool'
}

DEFAULT_LOCATION = 'INVALID'

BathsClass = namedtuple(
    'BathsClass',
    (
        'name', 'teacher', 'location',
        'description', 'start_time', 'end_time'
    )
)


def print_sep():
    print('_' * WIDTH)


def get_class_from_row(row):
    time, teacher, cost, title, description = (
        list(filter(None, div.text.split(os.linesep)))[0]
        for div in row.find_all('div')
    )

    location = DEFAULT_LOCATION
    for studio_class_index in range(3):
        class_ = 'light{}'.format(studio_class_index)
        if class_ in row.attrs['class']:
            location = STUDIO_LOOKUP[class_]

    if cost != INCLUDED_COST:
        return

    start_time, end_time = time.split(TIME_SEP)

    print('{} - {}\n\n{}\n'.format(teacher, title, fill(description, WIDTH)))
    print('{} to {}'.format(start_time, end_time))
    print('In {}'.format(location))
    print_sep()

    return BathsClass(
        title, teacher, location, description, start_time, end_time
    )


def dict_to_events(days_to_classes):
    today = datetime.date.today()
    today = datetime.datetime(
        year=today.year,
        month=today.month,
        day=today.day,
    )
    weekday = today.weekday()
    delta_to_monday = datetime.timedelta(days=weekday)
    mondays_date = today - delta_to_monday

    year_away = today + datetime.timedelta(days=365)

    events = []
    for day in days_to_classes.keys():
        for baths_class in days_to_classes[day]:
            if baths_class is None:
                continue

            start_time = strptime(baths_class.start_time, '%H:%M')
            start_delta = datetime.timedelta(
                hours=start_time.hour,
                minutes=start_time.minute
            )
            end_time = strptime(baths_class.end_time, '%H:%M')
            end_delta = datetime.timedelta(
                hours=end_time.hour,
                minutes=end_time.minute
            )
            duration = end_delta - start_delta

            day_of_week_delta = datetime.timedelta(
                days=DAYS_TO_OFFSET[day]
            )

            start_datetime = (mondays_date + day_of_week_delta) + start_delta

            event = Event()

            event.add(
                'summary', '{} with {}'
                ''.format(baths_class.name, baths_class.teacher)
            )
            event.add('description', baths_class.description)
            event.add('location', baths_class.location)
            event.add('dtstart', start_datetime)
            event.add('duration', duration)
            event.add('dtstamp', datetime.datetime.now())
            event.add('rrule', {'FREQ': 'weekly', 'UNTIL': year_away})

            events.append(event)

    return events


def main():
    result = requests.get(URL)
    code = result.status_code
    if code != SUCCESS:
        print('Requesting page failed, got code {}.'.format(code), out=stderr)
        exit(1)

    soup = BeautifulSoup(result.content, PARSER)
    table_div = soup.find('div', id=STUDIO_DIV)
    rows = table_div.find_all('div', attrs={'class': ROW_CLASS})

    days_to_classes = defaultdict(list)
    for row in rows:
        try:
            day = row.find('h2').text
            print_sep()
            print(day)
            print_sep()
        except AttributeError:
            days_to_classes[day].append(get_class_from_row(row))

    events = dict_to_events(days_to_classes)

    cal = Calendar()
    for event in events:
        cal.add_component(event)

    with open('calendar.ics', 'wb') as fd:
        fd.write(cal.to_ical())


if __name__ == '__main__':
    main()
