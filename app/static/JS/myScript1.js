const divs = document.querySelectorAll(".column.is-3-desktop.is-6-tablet");
//const backButtonTile = document.querySelectorAll(".backButtonTile");

function divStatus(){
    const statList = [];
    ele = document.querySelectorAll(".column.is-3-desktop.is-6-tablet");
    ele.forEach(el => {
        statList.push(el.style.display);     
    });
    return statList;
  }
  
  function hideScriptsBox(){
      scriptsBox = document.querySelectorAll(".flexbox-item-scripts");
      scriptsBox.forEach(div => {
            div.style.display = "none"; 
            div.classList.remove("column", "is-3-desktop", "is-6-tablet");
        });    
    }
  
  function workStationTableSize(widthSize){
    var wsTable = document.getElementById("workStationConTableId")
    wsTable.style.maxWidth = widthSize; 
  }

  
  function backButtonStatus(status, widthSize){
    var backButtonTile = document.querySelectorAll(".backButtonTile.childFlexBackButtonTile");
    backButtonTile.forEach(backButton => {
      backButton.style.display = status; 
    }); 
    workStationTableSize(widthSize)
  } 
  

  function backToMain(eventElement){
    divs.forEach(div => {
      console.log('inside backToMain function div child:',div.firstElementChild)
      div.firstElementChild.style.height = "auto";
    });
    vanish(eventElement)
  }

  function concatClass(cls){
        var newClass = ".flexbox-item-scripts-" + cls
        return newClass
    }

  function showBox(cls){
      boxClass = concatClass(cls)
      scriptsBox = document.querySelectorAll(boxClass);
      scriptsBox.forEach(div => {
          div.style.display = ""; 
          div.classList.add("column", "is-3-desktop", "is-6-tablet")
      });
  }
  
  function vanish(e) {
    hideScriptsBox()
    if(divStatus().includes('none')){
      divs.forEach(div => {
          div.style.display = "";   
          div.firstElementChild.style.height = "auto";
        });
      backButtonStatus('none', '')
      return
    }
    divs.forEach(div => {
      if (!(e.currentTarget === div)) {
          div.style.display = 'none';   
        }
    })
    backButtonStatus('block', '1210px')
    e.currentTarget.querySelector('div').style.height="14rem";
    window.boxRow = e.currentTarget.getAttribute('data-box-row');    
    showBox(boxRow)
  }
  
  function scriptOver(event) {       
    targetBoxRow =  "summary" + boxRow
    var summary = event.target.getAttribute('data-scriptSummary')
    try{
      var sensorSN = document.getElementById('SensorSN').value
    } catch(error){
      var sensorSN = ''
    }
    setValue(targetBoxRow, summary)
    try{
      document.getElementById('SensorSN').value = sensorSN
    }
    catch(error){
      
    }
  }

    function scriptOut() {
        targetBoxRow =  "summary" + boxRow
        console.log('')
        setValue(targetBoxRow, '')
    }

    function setValue(id,newvalue) {
      var s= document.getElementById(id);
      s.innerHTML = newvalue;
}  

function hideSection(boxRow){
  // hides section space pertaining to row
  extractDigit = boxRow.replace(/\D/g, '');
  if(extractDigit !== '') {
    num = Number(extractDigit);
  }
  if(num !==1){
    sectionClass = ".section-row-" + extractDigit
    console.log(sectionClass)
    secLoc = document.querySelector(sectionClass);
    secLoc.style.paddingTop = '0';
    console.log(num)
  }
  else{
    sectionReSize("none", '0') 
  }
}  

hideScriptsBox(), backButtonStatus('none')
var loc = document.querySelectorAll("h3[data-scriptsummary]");
loc.forEach(node => {
    node.addEventListener("mouseover", scriptOver);
    //node.addEventListener("mouseout", scriptOut);
})
divs.forEach(element => element.addEventListener('click', vanish));
//backButtonTopNavBar.addEventListener('click', backToMain);
//backButtonTopNavBar.addEventListener('click', vanish);

