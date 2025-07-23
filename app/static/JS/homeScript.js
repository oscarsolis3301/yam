document.addEventListener('DOMContentLoaded', () => {    
    function openModal($el) {
      $el.classList.add('is-active');   
      document.getElementById('hiddenOffice').focus();
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
    document.getElementById('DiagnosticPageModal').classList.remove('is-active');
    setTimeout(function(){
      document.getElementById('officeSearchForm').submit();
    }, 1000);
  }

  function userSub(){      
    document.getElementById('UserModal').classList.remove('is-active');
    setTimeout(function(){        
        document.getElementById("UserForm").submit();
    }, 1000);
}