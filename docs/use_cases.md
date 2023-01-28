# Use Cases for Doc Scraper

To better understand how Doc Scraper can be used, and as an aide during development, here some of the use cases.
The document structure is represented as code blocks in Markdown. `((comment))` is not part of the actual document but used to denote how the document is proceseed.

## Simple risk document

```
# Some risk document

## Some introduction

.......

## Section with data ((Only this section is processed))

### Risk 1

Some general description on risk 1.

| Title                           | Description          |
|---                              |---                   |
| Impact:  High((as dropdown))    | Some explanation     |
| Likely.: Low((as dropdown))     | Another explanation. |

### Risk 2

Some general description on risk 2.

A second paragraph of the description.

| Title                           | Description          |
|---                              |---                   |
| Impact:  Medium((as dropdown))  | ...                  |
| Likely.: Low((as dropdown))     | ...2...              |

```

Expected converted data (CSV):

| Name    | Description                                                                      |   Impact | Impact description |Likelihood | Likelihood description |
|---      | ---                                                                              |---       |        ---         |---        |---                     |
| Risk 1  | Some general description on risk 1.                                              | High     | Some explanation   | Low       | Another explanation.    |
| Risk 2  | Some general description on risk 2. <br/> A second paragraph of the description. | Medium   | ...                | High      | ...2...                    |

## Improvised, two-level todos

```
# Some todos

## Some introduction

......

## First goal

*   email1((as smart chip)): Do this [Pending((as dropdown))]

    Detailed description for to do this.

*   email1((as smart chip)): Do that [Done((as dropdown))]
*   email2((as smart chip)): Do something else [New((as dropdown))]

    Detailed description for to do something else.

## Second goal

*   email2((as smart chip)): Task 3 [Pending((as dropdown))]
*   email3((as smart chip)): Whatever other task [Done((as dropdown))]

```

Expected converted data (CSV):

| Goal        | Responsible | Summary               | Status   | Description                                    |
| ---         | ---         | ---                   | ---      | ---                                            |
| First goal  | email1      | Do this               | Pending  | Detailed description for to do this.           |
| First goal  | email1      | Do that               | Done     |                                                |
| First goal  | email2      | Do something else     | New      | Detailed description for to do something else. |
| Second goal | email2      | Task 3                | Pending  |                                                |
| Second goal | email3      | Whatever other task   | Done     |                                                |

## Supplies per location

```
# Supplies 

## Some introduction

Not really a relistic list but helps with the idea of going through a table per section.

## Location 1

Responsible: email1((as smart chip))

| Department   | Printers    | Laptops | Phones |
| ---          | ---         | ---     | ---    |
| Sales        | 5           | 20      | 25     |
| Procurement  | 10          | 5       | 18     |
| Accounting   | 2           | 3       | 8      |

## Location 2

Responsible: email2((as smart chip))

| Department   | Printers    | Laptops | Phones |
| ---          | ---         | ---     | ---    |
| Sales        | 4           | 17      | 29     |
| Procurement  | 2           | 10      | 1      |

```

Expected converted data (CSV):

| Location    | Responsible | Department    | Printers | Laptops | Phones |
| ---         | ---         | ---           | ---      | ---     | ---    |
| Location 1  | email1      | Sales         | 5        | 20      | 25     |
| Location 1  | email1      | Procurement   | 10       | 5       | 18     |
| Location 1  | email1      | Accounting    | 2        | 3       | 8      |
| Location 2  | email1      | Sales         | 4        | 5       | 29     |
| Location 2  | email1      | Procurement   | 2        | 3       | 1      |

If needed, the table can be "unpivoted":

| Location    | Responsible | Department    | Hardware type | Quantity |
| ---         | ---         | ---           | ---           | ---      |
| Location 1  | email1      | Sales         | Printers      | 5        |
| Location 1  | email1      | Sales         | Laptops       | 20       |
| Location 1  | email1      | Sales         | Phones        | 25       |
| Location 1  | email1      | Procurement   | Printers      | 10       |
| Location 1  | email1      | Procurement   | Laptops       | 5        |
| Location 1  | email1      | Procurement   | Phones        | 18       |
| ...         | ...         | ...           | ...           | ...      |
