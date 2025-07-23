document.addEventListener('DOMContentLoaded', () => {    
    function openModal($el) {
      $el.classList.add('is-active');   
      document.getElementById('workstationtext').focus();      
      document.getElementById('TicketOffice').focus();
      document.getElementById('usernametext').focus();     
      document.getElementById('officetext').focus();
      document.getElementById('SOPofficetext').focus();
      document.getElementById('CADofficetext').focus();
      document.getElementById('NETofficetext').focus();
      document.getElementById('SOPworkstationtext').focus();        
      document.getElementById('AdminUsername').focus();       
           
    }
  
    function closeModal($el) {
      $el.classList.remove('is-active');
    }
  
    function closeAllModals() {
      (document.querySelectorAll('.modal') || []).forEach(($modal) => {
        closeModal($modal);
      });
    }
  
    (document.querySelectorAll('.js-modal-trigger') || []).forEach(($trigger) => {
      const modal = $trigger.dataset.target;
      const $target = document.getElementById(modal);
  
      $trigger.addEventListener('click', () => {
        //document.getElementById('hiddenScript').value = $trigger.getAttribute('data-scriptvalue'); 
        openModal($target);          
      });
    });
  
    (document.querySelectorAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button') || []).forEach(($close) => {
      const $target = $close.closest('.modal');
  
      $close.addEventListener('click', () => {
        closeModal($target);
      });
    });
  
    document.addEventListener('keydown', (event) => {
      const e = event || window.event;
  
      if (e.keyCode === 27) { 
        closeAllModals();
      }
    });

    
  });
 
 function officeSearch(){
   document.getElementById('submitModal').classList.add('is-active');
   setTimeout(function(){
     document.getElementById('officeSearchForm').submit();
   }, 1000);
 }
 
 function cadDiagSubmit(){
   document.getElementById('cadDiagForm').submit();
 }
 function sensorDiagSubmit(){
    document.getElementById('sensorDiagForm').submit();
  }
 function clinicalDiagSubmit(){
    document.getElementById('clinicalDiagForm').submit();
 }
 function officeDiagSubmit(){
   document.getElementById('officeDiagForm').submit();
 }
 
 function netDiagSubmit(){
   document.getElementById('netDiagForm').submit();
 }
 
 function SolutionsSubmit(){
    document.getElementById('SolutionsForm').submit();
 }

 function NacSubmit(){
  document.getElementById('NacForm').submit();
}
 
 function ticketLookupCBCT(){
   document.getElementById('filterType').value='CBCT';
   document.getElementById('ticketSubmitModal').classList.add('is-active');
   setTimeout(function(){
     document.getElementById('officeTicketForm').submit();
   }, 1000);
 }
 
 function ticketLookupSensor(){
   document.getElementById('filterType').value='Sensor';
   document.getElementById('ticketSubmitModal').classList.add('is-active');
   setTimeout(function(){
     document.getElementById('officeTicketForm').submit();
   }, 1000);
 }
 
 function ticketLookupCerec(){
   document.getElementById('filterType').value='Cerec';
   document.getElementById('ticketSubmitModal').classList.add('is-active');
   setTimeout(function(){
     document.getElementById('officeTicketForm').submit();
   }, 1000);
 }

 function diagnosticChoice(){
    var diagnostic=document.querySelectorAll('input[name=diagnosticCheck]');
       len=diagnostic.length,
       i=0;
    for(i; i<len; i++){
       if(diagnostic[i].checked){
       document.getElementById(diagnostic[i].value).classList.remove('is-hidden');
       }
       else{
          document.getElementById(diagnostic[i].value).classList.add('is-hidden');
       };
    };
 }


 function sopActionSubmit(choice) {        
  var modal = document.getElementById("sopActionModal");
  modal.classList.remove('is-active');
};

function clinicalActionSubmit(choice) {        
  var modal = document.getElementById("clinicalActionModal");
  modal.classList.remove('is-active');
};

function sensorActionSubmit(choice) {        
  var modal = document.getElementById("sensorActionModal");
  modal.classList.remove('is-active');
};

function networkActionSubmit(choice) {        
  var modal = document.getElementById("networkActionModal");
  modal.classList.remove('is-active');
};

function ScriptFire(script, workstation, modal){
  var rows = document.getElementsByName('ScriptChoice'),
  len = rows.length,
  i=0;
  for(i; i<len; i++){
     rows[i].value=script;
  };

  document.getElementById(workstation).checked=true;

  document.getElementById(modal).classList.add('is-active');
}
