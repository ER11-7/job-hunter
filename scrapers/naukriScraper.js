// Naukri Scraper

const axios = require('axios');
const cheerio = require('cheerio');

const NAUKRI_URL = 'https://www.naukri.com/';

async function scrapeNaukri() {
    const { data } = await axios.get(NAUKRI_URL);
    const $ = cheerio.load(data);
    const jobs = [];

    $('.jobTuple').each((index, element) => {
        jobs.push({
            title: $(element).find('.jobTitle').text(),
            company: $(element).find('.companyName').text(),
            location: $(element).find('.location').text()
        });
    });

    return jobs;
}

module.exports = scrapeNaukri;