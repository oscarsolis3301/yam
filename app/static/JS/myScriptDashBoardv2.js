function removeSpace(list){
    var trimmed = [];
    for(var i=0;i<list.length;i++){
        if(list[i]){   
            let str = list[i].replace(/\s/g, '');
            trimmed.push(str)
        }
        else{
            return ["", ""]
        }
    }
    return trimmed
}

function validList(list){
    for(var i=0;i<list.length;i++){
        if(list[i] === "" || list[i] === 'N/A'){ 
            console.log('invalid data encountered: validList function', list[i])
            return false;
        }
    }
    return true;
};

function getParent(element){
    return element.parentNode;
  }

function getAncestor(elem, cls) {
    var found = false;
    var parent = null;
    parent = elem.parentNode;  
    while (found === false){ 
      if(parent.classList.contains(cls)){
        console.log('true');
        console.log(parent.classList)
        found = true;
    } else {
        console.log("false")
        console.log(parent.classList)
        parent = getParent(parent);
    }
  };
  return parent;
}

function idElement(id) {
    var elem = document.getElementById(id);
    console.log(elem)
    return elem
}

function elementByClass(cls){
    var targetClass = document.getElementsByClassName(cls);
    return targetClass[0]
    //return targetClass
}

function elementsByClass(cls){
    var targetClass = document.getElementsByClassName(cls);
    //return targetClass[0]
    return targetClass
}

function concatText(itemOne, itemTwo){
    var result = itemOne.concat(itemTwo); 
    return result
}

function respondClick(clickedId, elemClass){
    var clickedElem =window.event.target
    console.log('this elem was clicked ->',clickedElem) 
    console.log('id of the clicked elem ->',clickedId);
    elem = idElement(clickedId)
    console.log(elem)
    hiddenCardName = concatText(clickedId, '_card')
    console.log('class of elem to unhide ->',hiddenCardName)
    ancestor = getAncestor(clickedElem, elemClass)
    ancestor.classList.add("noDisplay")
    hiddenCard = elementByClass(hiddenCardName)
    console.log('elem to unhide found',hiddenCard)
    hiddenCard.classList.remove("noDisplay");
}

function respondClickCbct(clickedId){
    var clickedElem =window.event.target
    console.log('this elem was clicked ->',clickedElem)
    console.log('id of the clicked elem ->',clickedId);
    elem = idElement(clickedId)
    console.log(elem)
    hiddenClassName = concatText(clickedId, '_card')
    console.log('class of elem to unhide ->',hiddenClassName)
    ancestor = getAncestor(clickedElem, 'is-2')
    ancestorClassList= ancestor.classList
    ancestorClassList.forEach(function (elem) {
    if(`${elem}`.includes('cbct')){
        let cbctClassToHide = elem
        console.log('found it ->', elem)
        licenseCard = elementByClass(cbctClassToHide)
        licenseCard.classList.add("noDisplay")
    };
    });
    ancestor.classList.add("noDisplay")
    hiddenCards = elementsByClass(hiddenClassName)
    console.log('elems to unhide found',hiddenCards)
    for (var i = 0; i < hiddenCards.length; i++) {
        hiddenCards[i].classList.remove('noDisplay');
     }
}