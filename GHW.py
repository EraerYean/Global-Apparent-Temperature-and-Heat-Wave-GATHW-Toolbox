import cdstoolbox as ct
import calendar
import pandas
import datetime

# Get the data of the specified time and area, and resample by day.
def get_data(variable, grid, year, month, days, frequency, statistic, extent, tag):
    times = ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', 
            '06:00', '07:00', '08:00', '09:00', '10:00', '11:00', 
            '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', 
            '18:00', '19:00', '20:00', '21:00', '22:00', '23:00']
    timesSelect = []
    for index in range(0, len(times), frequency):
        timesSelect.append(times[index])
    #print(variable, year, month, days, timesSelect)
    data = ct.catalogue.retrieve(
        'reanalysis-era5-single-levels',
        {
            'variable': variable, 'grid': [grid, grid],
            'product_type': 'reanalysis',
            'year': year, 'month': month, 'day': days,
            'time': timesSelect
        }
    )
    if tag == 'AT':
        freq = 'day'
    elif tag == 'HW':
        freq = 'year'
    if statistic == 'Mean':
        data = ct.cube.resample(data, how = 'mean', freq = freq)
    elif statistic == 'Minimum':
        data = ct.cube.resample(data, how = 'min', freq = freq)
    elif statistic == 'Maximum':
        data = ct.cube.resample(data, how = 'max', freq = freq)
    if extent != {'lat': [-90, 90], 'lon': [-180, 180]}:
        data = ct.cube.select(
            data, extent = (
                extent['lon'][0], extent['lon'][1], 
                extent['lat'][0], extent['lat'][1]
            )
        )
    return data

# Get the data of the specified period and area, and resample by day.
def get_data_all(variable, grid, start, end, frequency, statistic, extent, tag):
    if tag == 'AT':
        months = pandas.date_range(start = start.replace(day = 1), end = end, freq = 'MS')
        if len(months) == 1:
            days = [day for day in range(start.day, end.day + 1)]
            data = get_data(variable, grid, months[0].year, months[0].month, days, frequency, statistic, extent, tag)
        if len(months) >= 2:
            daysStart = [day for day in range(start.day, calendar.monthrange(months[0].year, months[0].month)[1] + 1)]
            dataStart = get_data(variable, grid, months[0].year, months[0].month, daysStart, frequency, statistic, extent, tag)
            if len(months) >= 3:
                for month in months[1 : -1]:
                    daysMid = [day for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
                    dataMid = get_data(variable, grid, month.year, month.month, daysMid, frequency, statistic, extent, tag)
                    dataStart = ct.cube.concat([dataStart, dataMid], dim = 'time')
            daysEnd = [day for day in range(1, end.day + 1)]
            dataEnd = get_data(variable, grid, months[-1].year, months[-1].month, daysEnd, frequency, statistic, extent, tag)
            data = ct.cube.concat([dataStart, dataEnd], dim = 'time')
        return data
    elif tag == 'HW':
        years = [year for year in range(1991, 2021)]
        month = start.month
        day = start.day
        data = get_data(variable, grid, years, month, day, frequency, statistic, extent, tag)
        return data
    
def apparent_temperature(start, end, method, frequency, statistic, grid, unit, extent, tag):
    if method == 'Humidex TD':
        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataAT = dataTemp + 0.5555 * (6.11 * pow(2.718281828459, 5417.753 * ((1 / 273.15) - (1 / dataDewp))) - 10)
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        if unit == 'Kelvin (K)':
            dataAT = ct.cdm.convert_units(dataAT, 'Kelvin')
        elif unit == 'Fahrenheit (℉)':
            dataAT = ct.cdm.convert_units(dataAT, 'Fahrenheit')
        return dataAT
    elif method == 'Steadman TWP':
        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataWindU = get_data_all('10m_u_component_of_wind', grid, start, end, frequency, statistic, extent, tag)
        dataWindV = get_data_all('10m_v_component_of_wind', grid, start, end, frequency, statistic, extent, tag)
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataDewp = ct.cdm.convert_units(dataDewp, 'Celsius')
        dataHumi = (dataDewp + 19.2 - 0.84 * dataTemp) / (0.1980 + 0.0017 * dataTemp)
        dataPres = dataHumi / 100 * 6.105 * pow(2.718281828459, 17.27 * dataTemp / (237.7 + dataTemp))
        dataWind = pow(dataWindU * dataWindU + dataWindV * dataWindV, 0.5)
        dataAT = dataTemp + 0.33 * dataPres - 0.7 * dataWind - 4
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        if unit == 'Kelvin (K)':
            dataAT = ct.cdm.convert_units(dataAT, 'Kelvin')
        elif unit == 'Fahrenheit (℉)':
            dataAT = ct.cdm.convert_units(dataAT, 'Fahrenheit')
        return dataAT
    elif method == 'Steadman TWPR':
        dataTemp = get_data_all('2m_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataTemp = ct.cdm.convert_units(dataTemp, 'Celsius')
        dataWindU = get_data_all('10m_u_component_of_wind', grid, start, end, frequency, statistic, extent, tag)
        dataWindV = get_data_all('10m_v_component_of_wind', grid, start, end, frequency, statistic, extent, tag)
        dataDewp = get_data_all('2m_dewpoint_temperature', grid, start, end, frequency, statistic, extent, tag)
        dataDewp = ct.cdm.convert_units(dataDewp, 'Celsius')
        dataRadi = get_data_all('mean_surface_downward_short_wave_radiation_flux', grid, start, end, frequency, statistic, extent, tag)
        dataHumi = (dataDewp + 19.2 - 0.84 * dataTemp) / (0.1980 + 0.0017 * dataTemp)
        dataPres = dataHumi / 100 * 6.105 * pow(2.718281828459, 17.27 * dataTemp / (237.7 + dataTemp))
        dataWind = pow(dataWindU * dataWindU + dataWindV * dataWindV, 0.5)
        dataAT = dataTemp + 0.348 * dataPres - 0.7 * dataWind + 0.7 * dataRadi / (dataWind + 10) - 4.25
        dataAT = ct.cdm.update_attributes(dataAT, attrs = {'units': 'Celsius'})
        if unit == 'Kelvin (K)':
            dataAT = ct.cdm.convert_units(dataAT, 'Kelvin')
        elif unit == 'Fahrenheit (℉)':
            dataAT = ct.cdm.convert_units(dataAT, 'Fahrenheit')
        return dataAT

# Main function used to calculate heat wave.
def heatwave(start, end, methodHW, duraThre, tempThre, percThre, combThre, methodAT, frequency, statistic, grid, unit, extent):
    start = datetime.datetime.strptime(start, '%Y-%m-%d')
    end = datetime.datetime.strptime(end, '%Y-%m-%d')
    tempThreCom = int(combThre.replace(' ', '').split(',')[0])
    percThreCom = int(combThre.replace(' ', '').split(',')[1])
    if unit == 'Kelvin (K)':
        tempThre = tempThre + 273.15
        tempThreCom = tempThreCom + 273.15
    elif unit == 'Fahrenheit (℉)':
        tempThre = 1.8 * tempThre + 32
        tempThreCom = 1.8 * tempThreCom + 32
    data = apparent_temperature(start, end, methodAT, frequency, statistic, grid, unit, extent, 'AT')
    dataIni = ct.cube.index_select(data, time = 0)
    dataIni = 0
    dataTag = dataIni 
    dataTempSum = dataIni
    dataTempMax = dataIni
    dataFreq = dataIni
    dataDura = dataIni
    dataDmax = dataIni
    dataInte = dataIni
    dataTmax = dataIni
    dataStart = dataIni
    dataEnd = dataIni
    times = ct.cdm.get_coordinates(data)['time']['data']
    for index in range(len(times)):
        print(index)
        dataTimeValue = ct.cube.index_select(data, time = index)
        if methodHW == 'Constant threshold':
            dataTimeBool = ct.operator.ge(dataTimeValue, tempThre)
        elif methodHW == 'Percentile threshold':
            timeDate = datetime.datetime.strptime(times[index]['result'], '%Y-%m-%d %H:%M:%S')
            dataRef = apparent_temperature(timeDate, timeDate, methodAT, frequency, statistic, grid, unit, extent, 'HW')
            timesRef = ct.cdm.get_coordinates(dataRef)['time']['data']
            print(timeDate, timesRef)
            dataRef = ct.climate.climatology_perc(dataRef, percentiles = [percThre], frequency = 'dayofyear')
            dataRef = ct.cube.index_select(dataRef[0], dayofyear = 0)
            dataTimeBool = ct.operator.ge(dataTimeValue, dataRef)
        elif methodHW == 'Combined threshold':
            timeDate = datetime.datetime.strptime(times[index]['result'], '%Y-%m-%d %H:%M:%S')
            dataRef = apparent_temperature(timeDate, timeDate, methodAT, frequency, statistic, grid, unit, extent, 'HW')
            dataRef = ct.climate.climatology_perc(dataRef, percentiles = [percThreCom], frequency = 'dayofyear')
            dataRef = ct.cube.index_select(dataRef[0], dayofyear = 0)
            dataTimeBool = ct.cube.where((dataTimeValue >= tempThreCom) & (dataTimeValue >= dataRef), 1, 0)
        dataTag = ct.cube.where(dataTimeBool, dataTag + 1, dataTag)
        dataTempSum = ct.cube.where(dataTimeBool, dataTempSum + dataTimeValue, dataTempSum)
        dataTempSum = ct.cube.where((dataTimeBool == 0) & (dataTag < duraThre), 0, dataTempSum)
        dataTempMax = ct.cube.where(dataTimeBool, dataTimeValue, dataTempMax)
        dataTempMax = ct.cube.where((dataTimeBool == 0) & (dataTag < duraThre), 0, dataTempMax)
        dataTag = ct.cube.where((dataTimeBool == 0) & (dataTag < duraThre), 0, dataTag)
        dataFreq = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre), dataFreq + 1, dataFreq)
        dataDura = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre), dataDura + dataTag, dataDura)
        dataDmax = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre) & (dataTag > dataDmax), dataTag, dataDmax)
        dataInte = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre), dataInte + dataTempSum, dataInte)
        dataTmax = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre) & (dataTempMax > dataTmax), dataTempMax, dataTmax)
        doy = datetime.datetime.strptime(times[index]['result'], '%Y-%m-%d %H:%M:%S').strftime('%j')
        dataStart = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre) & (dataStart == 0), int(doy) - dataTag, dataStart)
        dataEnd = ct.cube.where(((dataTimeBool == 0) | (index == len(times) - 1)) & (dataTag >= duraThre), int(doy), dataEnd)
        dataTempSum = ct.cube.where((dataTimeBool == 0) & (dataTag >= duraThre), 0, dataTempSum)
        dataTag = ct.cube.where((dataTimeBool == 0) & (dataTag >= duraThre), 0, dataTag)
    dataFreq = ct.cube.where(dataFreq > 0, dataFreq)
    dataDura = ct.cube.where(dataFreq > 0, dataDura)
    dataDmax = ct.cube.where(dataFreq > 0, dataDmax)
    dataInte = dataInte / dataDura
    dataTmax = ct.cube.where(dataFreq > 0, dataTmax)
    dataStart = ct.cube.where(dataFreq > 0, dataStart)
    dataEnd = ct.cube.where(dataFreq > 0, dataEnd)
    if unit == 'Celsius (℃)':
        dataInte = ct.cdm.update_attributes(dataInte, attrs = {'units': 'Celsius'})
        dataTmax = ct.cdm.update_attributes(dataTmax, attrs = {'units': 'Celsius'})
    if unit == 'Kelvin (K)':
        dataInte = ct.cdm.update_attributes(dataInte, attrs = {'units': 'Kelvin'})
        dataTmax = ct.cdm.update_attributes(dataTmax, attrs = {'units': 'Kelvin'})
    elif unit == 'Fahrenheit (℉)':
        dataInte = ct.cdm.update_attributes(dataInte, attrs = {'units': 'Fahrenheit'})
        dataTmax = ct.cdm.update_attributes(dataTmax, attrs = {'units': 'Fahrenheit'})
    fig1 = ct.cdsplot.geomap(dataFreq, title = 'Heat wave frequency')
    fig2 = ct.cdsplot.geomap(dataDura, title = 'Heat wave duration')
    return data, dataFreq, dataDura, dataDmax, dataInte, dataTmax, dataStart, dataEnd, fig1, fig2

# Define application layout.
layout = ct.Layout(rows = 13, justify = 'center')
layout.add_widget(row = 0, content = 'start')
layout.add_widget(row = 0, content = 'end')
layout.add_widget(row = 0, content = 'grid')
layout.add_widget(row = 0, content = 'unit')
layout.add_widget(row = 1, content = 'frequency')
layout.add_widget(row = 1, content = 'statistic')
layout.add_widget(row = 1, content = 'methodAT')
layout.add_widget(row = 2, content = 'methodHW')
layout.add_widget(row = 2, content = 'tempThre')
layout.add_widget(row = 2, content = 'percThre')
layout.add_widget(row = 2, content = 'combThre')
layout.add_widget(row = 2, content = 'duraThre')
layout.add_widget(row = 3, content = 'extent')
layout.add_widget(row = 4, content = 'output-0')
layout.add_widget(row = 4, content = 'output-1')
layout.add_widget(row = 5, content = 'output-2')
layout.add_widget(row = 5, content = 'output-3')
layout.add_widget(row = 6, content = 'output-4')
layout.add_widget(row = 6, content = 'output-5')
layout.add_widget(row = 7, content = 'output-6')
layout.add_widget(row = 7, content = 'output-7')
layout.add_widget(row = 8, content = 'output-8')
layout.add_widget(row = 8, content = 'output-9')
layout.add_widget(row = 9, content = 'output-10')
layout.add_widget(row = 9, content = 'output-11')
layout.add_widget(row = 10, content = 'output-12')
layout.add_widget(row = 10, content = 'output-13')
layout.add_widget(row = 11, content = 'output-14')
layout.add_widget(row = 11, content = 'output-15')
layout.add_widget(row = 12, content = 'output-16')
layout.add_widget(row = 12, content = 'output-17')

@ct.application(title = 'Global Heat Wave Toolbox', layout = layout)
@ct.input.calendar('start', label = 'Start date', default = '2016-06-01', date_range = ['1979', '2021'], format = 'day')
@ct.input.calendar('end', label = 'End date', default = '2016-08-31', date_range = ['1979', '2021'], format = 'day')
@ct.input.dropdown('grid', label = 'Grid', values = [0.25, 0.5, 1])
@ct.input.dropdown('unit', label = 'Unit', values = ['Celsius (℃)', 'Kelvin (K)', 'Fahrenheit (℉)'])
@ct.input.dropdown('frequency', label = 'Frequency', values = [1, 2, 3, 4, 6], default = 4, help = 'The frequency of resampling hourly data to daily data.')
@ct.input.dropdown('statistic', label = 'Statistic', values = ['Mean', 'Minimum', 'Maximum'], help = 'The method of extracting daily meteorological variables.')
@ct.input.dropdown('methodAT', label = 'Apparent temperature method', values = ['Humidex TD', 'Steadman TWP', 'Steadman TWPR'], help = 'The method used to calculate apparent temperature.')
@ct.input.dropdown('methodHW', label = 'Heat wave method', values = ['Constant threshold', 'Percentile threshold', 'Combined threshold'], default = 'Combined threshold', link = True, help = 'The method used to calculate heat wave.')
@ct.input.dropdown('tempThre', label = 'Temperature threshold', values = range(25, 41), default = 29, when = 'Constant threshold')
@ct.input.dropdown('percThre', label = 'Percentile threshold', values = range(80, 96), when = 'Percentile threshold')
@ct.input.text('combThre', label = 'Combined threshold', default = '29, 85', when = 'Combined threshold', help = 'The first value is temperature threshold, the second is percentile threshold.')
@ct.input.dropdown('duraThre', label = 'Duration threshold', values = range(3, 8))
@ct.input.extent('extent', label = 'Extent', default = {'lat': [-90, 90], 'lon': [-180, 180]}, compact = True)
@ct.output.markdown()
@ct.output.markdown()
@ct.output.download()
@ct.output.download()
@ct.output.markdown()
@ct.output.markdown()
@ct.output.download()
@ct.output.download()
@ct.output.markdown()
@ct.output.markdown()
@ct.output.download()
@ct.output.download()
@ct.output.markdown()
@ct.output.markdown()
@ct.output.download()
@ct.output.download()
@ct.output.figure()
@ct.output.figure()

# Main application method.
def calculator(start, end, grid, unit, frequency, statistic, extent, methodAT, methodHW, duraThre, tempThre = 0, percThre = 0, combThre = '29, 85'):
    dataAT, dataFreq, dataDura, dataDmax, dataInte, dataTmax, dataStart, dataEnd, fig1, fig2 = heatwave(start, end, methodHW, duraThre, tempThre, percThre, combThre, methodAT, frequency, statistic, grid, unit, extent)
    text1 = 'Apparent temperature'
    text2 = 'Heat wave frequency'
    text3 = 'Heat wave duration'
    text4 = 'Heat wave longest duration'
    text5 = 'Heat wave intensity'
    text6 = 'Heat wave amplitude'
    text7 = 'Heat wave start date'
    text8 = 'Heat wave end date'
    return text1, text2, dataAT, dataFreq, text3, text4, dataDura, dataDmax, text5, text6, dataInte, dataTmax, text7, text8, dataStart, dataEnd, fig1, fig2