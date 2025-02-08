export const handler = async (event, context) => {

    const length = event.length;
    const width = event.width;
    let area = calculateArea(length, width);
    console.log(`The area is ${area}`); 

    console.log('CloudWatch log group name:', context.logGroupName);

    let data = {
        "area": area,
    };

        return JSON.stringify(data);

    function calculateArea(length, width) {
        return length * width;
    }

};