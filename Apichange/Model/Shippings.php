<?php

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\ShippingInterface;
use \Magento\Framework\App\Config\ScopeConfigInterface;
use \Magento\Shipping\Model\Config;

class Shippings implements ShippingInterface
{
    protected $shipconfig;

    protected $scopeConfig;

    public function __construct(
        \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig,
        \Magento\Store\Model\StoreManagerInterface $storeManager,
        \Magento\Shipping\Model\Config $shipconfig
    ) {
        $this->shipconfig = $shipconfig;
        $this->_storeManager = $storeManager;
        $this->scopeConfig = $scopeConfig;
    }
    public function getWebsiteLists()
    {
        $collection = $this->_websiteCollectionFactory->create();
        return $collection;
    }
    public function shipping()
    {
        $storeManagerDataList = $this->_storeManager->getStores();
        foreach ($storeManagerDataList as $store) {
            $activeCarriers = $this->shipconfig->getAllCarriers($store->getId());
            $storeScope = \Magento\Store\Model\ScopeInterface::SCOPE_STORE;
            foreach ($activeCarriers as $carrierCode => $carrierModel) {
                $options = array();
                if ($carrierMethods = $carrierModel->getAllowedMethods()) {
                    foreach ($carrierMethods as $methodCode => $method) {
                        $code = $carrierCode . '_' . $methodCode;
                        $options[] = array('value' => $code, 'label' => $method);

                    }
                    $carrierTitle = $this->scopeConfig->getValue('carriers/' . $carrierCode . '/title');

                }
                $methods[] = array('value' => $options, 'label' => $carrierTitle, 'store' => (int) $store->getId());
            }
        }
        return $methods;
    }
}
