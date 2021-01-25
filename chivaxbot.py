import os
import requests
import csv
import json
import pytz

from cairosvg import svg2png
from datetime import date, datetime, timedelta
import numpy as np

# source: https://data.cityofchicago.org/Health-Human-Services/COVID-19-Vaccine-Doses-by-ZIP-Code-Series-Complete/8u6c-48j3
vax_url = "https://data.cityofchicago.org/api/views/553k-3xzc/rows.json?accessType=DOWNLOAD"
vax_svg_path = os.path.join(os.getcwd(), "data", "zipcodes-vax.svg")

# source: https://data.cityofchicago.org/Health-Human-Services/COVID-19-Cases-Tests-and-Deaths-by-ZIP-Code/yhhz-zm2v
deaths_url= "https://data.cityofchicago.org/api/views/yhhz-zm2v/rows.json?accessType=DOWNLOAD"
deaths_svg_path = os.path.join(os.getcwd(), "data", "zipcodes-deaths.svg")

vax_colorscale = ["#feebe2", "#fbb4b9", "#f768a1", "#c51b8a", "#7a0177"]
deaths_colorscale =  ["#feebe2", "#f3cea3", '#f3b875', '#C83302', '#992702']

now = datetime.now(pytz.timezone('America/Chicago'))
yesterday = (now - timedelta(days = 1))
vax_output_path = os.path.join(os.getcwd(), "exports", "vax-{}.png".format(
    now.strftime("%Y-%m-%d-%H%M")
))
deaths_output_path = os.path.join(os.getcwd(), "exports", "deaths-{}.png".format(
    now.strftime("%Y-%m-%d-%H%M")
))

def get_tweet():
    vax_res = requests.get(vax_url)
    vax_res_json = json.loads(vax_res.text)

    deaths_res = requests.get(deaths_url)
    deaths_res_json = json.loads(deaths_res.text)

    # loop over city data and return a dictionary of zipcodes and their vax rates
    # also, a sum of all vaccinations
    vax_perc = {}
    vax_sum = 0
    population_sum = 0
    max_date = max([datetime.strptime(i[9], '%Y-%m-%dT00:00:00') for i in vax_res_json["data"]])
    for row in vax_res_json["data"]:
        # we only want dose cumulatives from the latest date
        # res date should be in the format 2021-01-18T00:00:00
        if max_date == datetime.strptime(row[9], '%Y-%m-%dT00:00:00'):
            vax_perc[row[8]] = float(row[17])
            vax_sum += int(row[16])
            population_sum += int(row[18])

    deaths_perc = {}
    deaths_sum = 0
    max_week = max([int(i[9]) for i in deaths_res_json["data"]])
    for row in deaths_res_json["data"]:
        if max_week == int(row[9]):
            # take "death rate per 100,000 population through the week"
            deaths_perc[row[8]] = float(row[25])
            deaths_sum += int(row[23])

    # then, create a dictionary of zip codes and colors
    vax_colors = get_colors_dict(vax_perc, vax_colorscale)
    deaths_colors = get_colors_dict(deaths_perc, deaths_colorscale)

    write_svg(vax_svg_path, vax_output_path, vax_colors)
    write_svg(deaths_svg_path, deaths_output_path, deaths_colors)

    percent_vaccinated = vax_sum / population_sum * 100
    tweet_text = "Chicago is currently reporting {vaccinations} people fully vaccinated: {percent}% of the population\n\nWho is dying:           Who is vaccinated:".format(
        vaccinations=f'{vax_sum:,}',
        percent=round(percent_vaccinated, 1),
    )

    alt_text = '''
    Two maps of Chicago, side by side. The map on the left shows COVID-19 deaths
    per capita by ZIP code. The map on the right shows completed COVID-19
    vaccination per capita by ZIP code. The maps reveal a disconnect between
    where residents are getting vaccinated and where COVID-19 deaths are
    concentrated.
    '''

    return {
        "tweet_text": tweet_text,
        "deaths_map_path": deaths_output_path,
        "vax_map_path": vax_output_path,
        "alt_text": alt_text
    }


def get_colors_dict(values_dict, colorscale):
    colors_dict = {}
    arr = list(values_dict.values())
    for name, value in values_dict.items():
        # prepend "zip" to make these names less confusing
        # when they appear in the SVG
        svg_name = "zip{}".format(name)

        # divide results into 5 even percentiles
        if (value < np.percentile(arr, 20)):
            colors_dict[svg_name] = colorscale[0]
        elif (value < np.percentile(arr, 40)):
            colors_dict[svg_name] = colorscale[1]
        elif (value < np.percentile(arr, 60)):
            colors_dict[svg_name] = colorscale[2]
        elif (value < np.percentile(arr, 80)):
            colors_dict[svg_name] = colorscale[3]
        elif (value <= np.percentile(arr, 100)):
            colors_dict[svg_name] = colorscale[4]
        else:
            colors_dict[svg_name] = "white"

    return colors_dict


def write_svg(svg_path, output_path, colors_dict):
    # write colors into the SVG file and export
    with open(svg_path, "r") as svg_file:
        svg_string = svg_file.read().format(**colors_dict)
        svg2png(
            bytestring=svg_string,
            write_to=output_path,
            background_color="white",
        )
