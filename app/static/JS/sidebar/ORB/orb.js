// Adapted from
// https://codepen.io/pekopekopeko/pen/PbYRWps

const el = document.getElementById('canvas');
const ctx = el.getContext('2d');
const dpr = window.devicePixelRatio || 1;
const pi = Math.PI;
const points = 12;
const radius = 200 * dpr;
const h = 600 * dpr;
const w = 600 * dpr;
const center = {
    x: w / 2 * dpr, 
    y: h / 2 * dpr
};
const circles = [];
const rangeMin = 1;
const rangeMax = 30;
const showPoints = true;

let mouseY = 0;
let tick = 0;

const gradient1 = ctx.createLinearGradient(0, 0, w, 0);
gradient1.addColorStop(0, '#96fbc4');
gradient1.addColorStop(1, '#f9f586');

const gradient2 = ctx.createLinearGradient(0, 0, w, 0);
gradient2.addColorStop(0, '#48c6ef');
gradient2.addColorStop(1, '#6f86d6');

const gradient3 = ctx.createLinearGradient(0, 0, w, 0);
gradient3.addColorStop(0, '#9795f0');
gradient3.addColorStop(1, '#9be15d');

const gradient4 = ctx.createLinearGradient(0, 0, w, 0);
gradient4.addColorStop(0, '#f6d365');
gradient4.addColorStop(1, '#fda085');

const gradients = [ gradient1, gradient2, gradient3, gradient4 ];

window.addEventListener('mousemove', handleMove, true);

function handleMove(event) {
    mouseY = event.clientY;
}

ctx.scale(dpr, dpr);

el.width = w * dpr;
el.height = h * dpr;
el.style.width = w + 'px';
el.style.height = h + 'px';

// Setup swing circle points

for (var idx = 0; idx <= gradients.length - 1; idx++) {
  
    let swingpoints = [];
    let radian = 0;

    for (var i = 0; i < points; i++){
        radian = pi * 2 / points * i;
        var ptX = center.x + radius * Math.cos(radian);
        var ptY = center.y + radius * Math.sin(radian);

        swingpoints.push({ 
            x: ptX,
            y: ptY,
            radian: radian,
            range: random(rangeMin, rangeMax),
            phase: 0 
        });
    }
  
    circles.push(swingpoints);

}

// --------------------------------------------------------------------------- //
// swingCircle

function swingCircle() {
    ctx.clearRect(0, 0, w * dpr, h * dpr);
    
    ctx.globalAlpha = 1;
    // ctx.globalCompositeOperation = 'source-over';
    ctx.globalCompositeOperation = 'screen';
    
    for (let k = 0; k < circles.length; k++) {
        let swingpoints = circles[k];
      
        for (var i = 0; i < swingpoints.length; i++){
            swingpoints[i].phase += random(1, 10) * -0.01;
            
            let phase = 4 * Math.sin(tick / 65);
            
            if (mouseY !== 0) {
                phase = mouseY / 200 + 1;
            }
            
            var r = radius + (swingpoints[i].range * phase * Math.sin(swingpoints[i].phase)) - rangeMax;
            
            swingpoints[i].radian += pi / 360;
            
            var ptX = center.x + r * Math.cos(swingpoints[i].radian);
            var ptY = center.y + r * Math.sin(swingpoints[i].radian);
    
            if (showPoints === true) {
                ctx.strokeStyle = '#96fbc4';

                ctx.beginPath();
                ctx.arc(ptX, ptY, 2 * dpr, 0, pi * 2, true);
                ctx.closePath();
                ctx.stroke();
            }
                
            swingpoints[i] = {
                x: ptX,
                y: ptY,
                radian: swingpoints[i].radian,
                range: swingpoints[i].range,
                phase: swingpoints[i].phase,
            };
        }

        const fill = gradients[k];
    
        drawCurve(swingpoints, fill);
      
    }
    
    tick++;
    
    requestAnimationFrame(swingCircle);
}

requestAnimationFrame(swingCircle);


// --------------------------------------------------------------------------- //
// drawCurve

function drawCurve(pts, fillStyle) {
    ctx.fillStyle = fillStyle;
    ctx.beginPath();
    ctx.moveTo(
        (pts[cycle( - 1, points)].x + pts[0].x) / 2,
        (pts[cycle( - 1, points)].y + pts[0].y) / 2);
    for (var i = 0; i < pts.length; i++){
      
        ctx.quadraticCurveTo(
            pts[i].x,
            pts[i].y,
            (pts[i].x + pts[cycle(i + 1, points)].x) / 2,
            (pts[i].y + pts[cycle(i + 1, points)].y) / 2);
    }
  
  ctx.closePath();
  ctx.fill();

}

// --------------------------------------------------------------------------- //
// cycle
function cycle( num1, num2 ) {
    return ( num1 % num2 + num2 ) % num2;
}

// --------------------------------------------------------------------------- //
// random
function random (num1, num2) {
    var max = Math.max(num1, num2);
    var min = Math.min(num1, num2);
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// --------------------------------------------------------------------------- //
// rotate

// function rotate (x, y, angle) {
//     var radians = (pi / 180) * angle,
//         cos = Math.cos(radians),
//         sin = Math.sin(radians),
//         nx = (cos * (x - center.x)) + (sin * (y - center.y)) + center.x,
//         ny = (cos * (y - center.y)) - (sin * (x - center.x)) + center.y;
//     return { x: nx, y: ny };
// }