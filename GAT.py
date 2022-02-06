import cdstoolbox as ct
import pandas
import calendar
import datetime
import numpy as np

# Get the data of the specified time and area, and resample by day.
def get_data(variable, grid, year, month, days, frequency, statistic, extent):
    times = ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', 
            '06:00', '07:00', '08:00', '09:00', '10:00', '11:00', 
            '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', 
            '18:00', '19:00', '20:00', '21:00', '22:00', '23:00']
    timesSelect = []
    for index in range(0, len(times), frequency):
        timesSelect.append(times[index])
    print(variable, year, month, days, timesSelect)
    data = ct.catalogue.retrieve(
        'reanalysis-era5-single-levels',
        {
            'variable': variable, 'grid': [grid, grid],
            'product_type': 'reanalysis',
            'year': year, 'month': month, 'day': days,
            'time': timesSelect
        }
    )
    if statistic == 'Mean':
        data = ct.climate.daily_mean(data)
    elif statistic == 'Minimum':
        data = ct.climate.daily_min(data)
    elif statistic == 'Maximum':
        data = ct.climate.daily_max(data)
    if extent != {'lat': [-90, 90], 'lon': [-180, 180]}:
        data = ct.cube.select(
            data, extent = (
                extent['lon'][0], extent['lon'][1], 
                extent['lat'][0], extent['lat'][1]
            )
        )
    return data

# Get the data of the specified period and area, and resample by day.
def get_data_all(variable, grid, start, end, frequency, statistic, extent):
    months = pandas.date_range(start = start.replace(day = 1), end = end, freq = 'MS')
    if len(months) == 1:
        days = [day for day in range(start.day, end.day + 1)]
        data = get_data(variable, grid, months[0].year, months[0].month, days, frequency, statistic, extent)
    if len(months) >= 2:
        daysStart = [day for day in range(start.day, calendar.monthrange(months[0].year, months[0].month)[1] + 1)]
        dataStart = get_data(variable, grid, months[0].year, months[0].month, daysStart, frequency, statistic, extent)
        if len(months) >= 3:
            for month in months[1 : -1]:
                daysMid = [day for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
                dataMid = get_data(variable, grid, month.year, month.month, daysMid, frequency, statistic, extent)
                dataStart = ct.cube.concat([dataStart, dataMid], dim = 'time')
        daysEnd = [day for day in range(1, end.day + 1)]
        dataEnd = get_data(variable, grid, months[-1].year, months[-1].month, daysEnd, frequency, statistic, extent)
        data = ct.cube.concat([dataStart, dataEnd], dim = 'time')
    return data

# Process apparent temperature data.
def process_apparent_temperature(dataAT, unit, city, start):
    dataATMonth = ct.climate.monthly_mean(dataAT)
    if unit == 'Kelvin (K)':
        dataAT = ct.cdm.convert_units(dataAT, 'Kelvin')
        dataATMonth = ct.cdm.convert_units(dataATMonth, 'Kelvin')
    elif unit == 'Fahrenheit (℉)':
        dataAT = ct.cdm.convert_units(dataAT, 'Fahrenheit')
        dataATMonth = ct.cdm.convert_units(dataATMonth, 'Kelvin')
    dataATMonth = ct.cube.index_select(dataATMonth, time = 0)
    fig1 = ct.cdsplot.geomap(dataATMonth, title = 'Apparent temperature (' + str(start)[0: 7] + ')')
    dataATCity = ct.geo.extract_point(dataAT, lon = city['lon'], lat = city['lat'])
    fig2 = ct.chart.line(dataATCity, layout_kwargs = {'title': 'Apparent temperature (' + city['value'] + ')'})
    times = ct.cdm.get_coordinates(dataATCity)['time']['data']
    values = []
    for index in range(len(times)):
        value = ct.cdm.get_value(dataATCity, index = index)['value']
        values.append(value)
    print(values)
    return dataATMonth, fig1, fig2

# Calculate apparent temperature.
def apparent_temperature(start, end, method, frequency, statistic, grid, unit, extent, city):
    if method == 'Humidex TD':
        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent)
        dataAT = dataTemp + 0.5555 * (6.11 * pow(np.e, 5417.753 * ((1 / 273.15) - (1 / dataDewp))) - 10)
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        dataATMonth, fig1, fig2 = process_apparent_temperature(dataAT, unit, city, start)
        return dataAT, dataATMonth, fig1, fig2
    elif method == 'Steadman TWP':
        variables = ['2m_temperature', '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature']



        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataWindU = get_data_all('10m_u_component_of_wind', grid, start, end, frequency, statistic, extent)
        dataWindV = get_data_all('10m_v_component_of_wind', grid, start, end, frequency, statistic, extent)
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent)
        dataDewp = ct.cdm.convert_units(dataDewp, 'Celsius')
        dataHumi = (dataDewp + 19.2 - 0.84 * dataTemp) / (0.1980 + 0.0017 * dataTemp)
        dataPres = dataHumi / 100 * 6.105 * pow(np.e, 17.27 * dataTemp / (237.7 + dataTemp))
        dataWind = pow(dataWindU * dataWindU + dataWindV * dataWindV, 0.5)
        dataAT = dataTemp + 0.33 * dataPres - 0.7 * dataWind - 4
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        dataATMonth, fig1, fig2 = process_apparent_temperature(dataAT, unit, city, start)
        return dataAT, dataATMonth, fig1, fig2
    elif method == 'Steadman TWPR':
        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataWindU = get_data_all('10m_u_component_of_wind', grid, start, end, frequency, statistic, extent)
        dataWindV = get_data_all('10m_v_component_of_wind', grid, start, end, frequency, statistic, extent)
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent)
        dataDewp = ct.cdm.convert_units(dataDewp, 'Celsius')
        dataRadi = get_data_all('mean_surface_downward_short_wave_radiation_flux', grid, start, end, frequency, statistic, extent)
        dataHumi = (dataDewp + 19.2 - 0.84 * dataTemp) / (0.1980 + 0.0017 * dataTemp)
        dataPres = dataHumi / 100 * 6.105 * pow(np.e, 17.27 * dataTemp / (237.7 + dataTemp))
        dataWind = pow(dataWindU * dataWindU + dataWindV * dataWindV, 0.5)
        dataAT = dataTemp + 0.348 * dataPres - 0.7 * dataWind + 0.7 * dataRadi / (dataWind + 10) - 4.25
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        dataATMonth, fig1, fig2 = process_apparent_temperature(dataAT, unit, city, start)
        return dataAT, dataATMonth, fig1, fig2

# Define application layout.
layout = ct.Layout(rows = 6, justify = 'center')
layout.add_widget(row = 0, content = 'start')
layout.add_widget(row = 0, content = 'end')
layout.add_widget(row = 0, content = 'grid')
layout.add_widget(row = 1, content = 'unit')
layout.add_widget(row = 1, content = 'frequency')
layout.add_widget(row = 1, content = 'statistic')
layout.add_widget(row = 1, content = 'method')
layout.add_widget(row = 2, content = 'extent')
layout.add_widget(row = 3, content = 'city')
layout.add_widget(row = 4, content = 'output-0')
#layout.add_widget(row = 4, content = 'output-1')
layout.add_widget(row = 5, content = 'output-1')
layout.add_widget(row = 5, content = 'output-2')

@ct.application(title = 'Global Apparent Temperature Toolbox', layout = layout)
@ct.input.calendar('start', label = 'Start date', default = '2007-01-01', date_range = ['1979', '2021'], format = 'day')
@ct.input.calendar('end', label = 'End date', default = '2007-12-31', date_range = ['1979', '2021'], format = 'day')
@ct.input.dropdown('grid', label = 'Grid', values = [0.25, 0.5, 1])
@ct.input.dropdown('unit', label = 'Unit', values = ['Celsius (℃)', 'Kelvin (K)', 'Fahrenheit (℉)'])
@ct.input.dropdown('frequency', label = 'Frequency', values = [1, 2, 3, 4, 6], help = 'The frequency of resampling hourly data to daily data.')
@ct.input.dropdown('statistic', label = 'Statistic', values = ['Mean', 'Minimum', 'Maximum'], help = 'The method of extracting daily meteorological variables.')
@ct.input.dropdown('method', label = 'Method', values = ['Humidex TD', 'Steadman TWP', 'Steadman TWPR'], help = 'The method used to calculate apparent temperature.')
@ct.input.extent('extent', label = 'Extent', default = {'lat': [-90, 90], 'lon': [-180, 180]}, compact = True)
@ct.input.city('city', label = 'City', default = 'New York City', help = 'The location of the selected city must not exceed the space defined by "Extent".')
@ct.output.download()
#@ct.output.download()
@ct.output.figure()
@ct.output.livefigure()

# Main application method.
def calculator(start, end, method, frequency, statistic, grid, unit, extent, city):
    start = datetime.datetime.strptime(start, '%Y-%m-%d')
    end = datetime.datetime.strptime(end, '%Y-%m-%d')    
    dataAT, dataATMonth, fig1, fig2 = apparent_temperature(start, end, method, frequency, statistic, grid, unit, extent, city)
    dataATMonth = ct.cdm.netcdf_to_raster(dataATMonth)
    return dataAT, fig1, fig2